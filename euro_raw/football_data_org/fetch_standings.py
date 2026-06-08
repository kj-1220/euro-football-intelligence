#!/usr/bin/env python3
"""
euro_raw/football_data_org/fetch_standings.py

Bronze ingestion: football-data.org -> euro_raw.fdorg_standings

One call per competition per season returns final (or current) standings.
matchweek is taken from season.currentMatchday in the API response.

Tier A — no floor.

Note: fdorg_standings has no UNIQUE constraint in the spec, so idempotency
is handled by skipping any (competition_id, season) pair already present.
"""

from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
import requests
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

_HERE      = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_ENV_PATH  = _REPO_ROOT / ".env"
load_dotenv(_ENV_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

SEASONS: list[int] = [2023, 2024, 2025]

COMPETITIONS: dict[str, str] = {
    "PL":  "Premier League",
    "PD":  "La Liga",
    "BL1": "Bundesliga",
    "SA":  "Serie A",
    "FL1": "Ligue 1",
}

FDORG_BASE_URL        = "https://api.football-data.org/v4"
REQUEST_DELAY_SECONDS = 7

# ── Helpers ──────────────────────────────────────────────────────────────────

def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def get_db_conn():
    dsn = os.getenv("POSTGRES_URL")
    if not dsn:
        raise EnvironmentError(f"POSTGRES_URL not set. Looked at: {_ENV_PATH}")
    return psycopg2.connect(dsn)


@retry(
    retry=retry_if_exception_type(requests.HTTPError),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def fdorg_get(path: str, api_key: str, params: dict = None) -> dict:
    url  = f"{FDORG_BASE_URL}{path}"
    resp = requests.get(
        url,
        headers={"X-Auth-Token": api_key},
        params=params or {},
        timeout=30,
    )
    if resp.status_code == 429:
        log.warning("429 rate-limited — backing off.")
        resp.raise_for_status()
    if resp.status_code == 403:
        raise PermissionError(f"403 Forbidden — check FOOTBALL_DATA_API_KEY.\nURL: {url}")
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    return resp.json()


def already_ingested(cur, competition_id: str, season_str: str) -> bool:
    """True if any rows exist for this competition + season — skip on re-run."""
    cur.execute(
        """
        SELECT 1 FROM euro_raw.fdorg_standings
        WHERE competition_id = %s AND season = %s
        LIMIT 1
        """,
        (competition_id, season_str),
    )
    return cur.fetchone() is not None


def write_standings(
    cur,
    table: list,
    competition_id: str,
    season_str: str,
    matchweek: int,
) -> int:
    if not table:
        return 0

    rows = [
        (
            season_str,
            competition_id,
            matchweek,
            f"fdorg_{row['team']['id']}",
            row.get("position"),
            row.get("playedGames"),
            row.get("won"),
            row.get("draw"),
            row.get("lost"),
            row.get("goalsFor"),
            row.get("goalsAgainst"),
            row.get("goalDifference"),
            row.get("points"),
            row.get("form"),
        )
        for row in table
        if (row.get("team") or {}).get("id")
    ]

    if not rows:
        return 0

    execute_values(
        cur,
        """
        INSERT INTO euro_raw.fdorg_standings
            (season, competition_id, matchweek, club_id,
             position, played, won, drawn, lost,
             goals_for, goals_against, goal_difference, points, form)
        VALUES %s
        """,
        rows,
    )
    return len(rows)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Loading .env from: %s (exists=%s)", _ENV_PATH, _ENV_PATH.exists())

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise EnvironmentError(f"FOOTBALL_DATA_API_KEY not set. Looked at: {_ENV_PATH}")

    conn = get_db_conn()
    conn.autocommit = False
    log.info("Connected.")
    log.info("Seasons : %s", [season_label(y) for y in SEASONS])
    log.info("Comps   : %s", list(COMPETITIONS.keys()))
    log.info("")

    total_rows = 0
    errors     = []
    skipped    = []

    try:
        for code, name in COMPETITIONS.items():
            for season_year in SEASONS:
                label = season_label(season_year)
                log.info("── %s  %s  (season=%d) ──", name, label, season_year)

                try:
                    payload = fdorg_get(
                        f"/competitions/{code}/standings",
                        api_key,
                        params={"season": season_year},
                    )
                except PermissionError as exc:
                    log.error("%s", exc)
                    raise
                except Exception as exc:
                    msg = f"{code} {label}: {exc}"
                    log.error("  ✗  %s", msg)
                    errors.append(msg)
                    continue

                comp_meta      = payload.get("competition") or {}
                season_meta    = payload.get("season") or {}
                competition_id = f"fdorg_{comp_meta.get('id', code)}"
                matchweek      = season_meta.get("currentMatchday") or 0

                # TOTAL only — HOME and AWAY are derivable in Silver
                standings_list = payload.get("standings") or []
                total_table    = next(
                    (s.get("table", []) for s in standings_list if s.get("type") == "TOTAL"),
                    [],
                )

                with conn.cursor() as cur:
                    if already_ingested(cur, competition_id, label):
                        log.info("  ↷  already ingested — skipping")
                        skipped.append(f"{code} {label}")
                        continue

                    n = write_standings(cur, total_table, competition_id, label, matchweek)
                    total_rows += n

                conn.commit()
                log.info("  ✓  %d rows  |  matchweek=%d  |  committed", n, matchweek)

    except Exception:
        conn.rollback()
        log.error("Rolled back.")
        raise
    finally:
        conn.close()

    log.info("")
    log.info("═" * 60)
    log.info("Done. %d total rows inserted.", total_rows)
    if skipped:
        log.info("Skipped (already present): %s", skipped)
    if errors:
        log.warning("%d error(s):", len(errors))
        for e in errors:
            log.warning("  • %s", e)
    log.info("═" * 60)


if __name__ == "__main__":
    main()