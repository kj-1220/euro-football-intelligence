#!/usr/bin/env python3
"""
euro_raw/football_data_org/fetch_matches.py

Bronze ingestion: football-data.org -> euro_raw schema

Writes to:
  euro_raw.fdorg_matches      (Tier A — primary target)
  euro_raw.competitions       (reference table)
  euro_raw.clubs              (reference table)

Bronze rules:
  - Append-only: ON CONFLICT DO NOTHING everywhere
  - No transforms: source fields written as received
  - ingested_at handled by column DEFAULT NOW()
  - All source IDs namespaced as fdorg_{id}

Seasons:
  2023 -> 2023-24
  2024 -> 2024-25
  2025 -> 2025-26
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

# ── Load .env from repo root (two levels up from this file) ──────────────────
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_ENV_PATH = _REPO_ROOT / ".env"
load_dotenv(_ENV_PATH)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

SEASONS: list[int] = [2023, 2024, 2025]
# 2023 -> 2023-24  |  2024 -> 2024-25  |  2025 -> 2025-26

COMPETITIONS: dict[str, str] = {
    "PL":  "Premier League",
    "PD":  "La Liga",
    "BL1": "Bundesliga",
    "SA":  "Serie A",
    "FL1": "Ligue 1",
}

FDORG_BASE_URL = "https://api.football-data.org/v4"
REQUEST_DELAY_SECONDS = 7  # free tier: 10 req/min -> 6 s min; 7 s headroom

# ── Helpers ──────────────────────────────────────────────────────────────────

def season_label(year: int) -> str:
    """2023 -> '2023-24'"""
    return f"{year}-{str(year + 1)[-2:]}"


def get_db_conn():
    dsn = os.getenv("POSTGRES_URL")
    if not dsn:
        raise EnvironmentError(
            "POSTGRES_URL is not set in .env\n"
            f"Looked at: {_ENV_PATH}"
        )
    return psycopg2.connect(dsn)


@retry(
    retry=retry_if_exception_type(requests.HTTPError),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def fdorg_get(path: str, api_key: str, params: dict = None) -> dict:
    url = f"{FDORG_BASE_URL}{path}"
    resp = requests.get(
        url,
        headers={"X-Auth-Token": api_key},
        params=params or {},
        timeout=30,
    )
    if resp.status_code == 429:
        log.warning("429 rate-limited — tenacity will back off and retry.")
        resp.raise_for_status()
    if resp.status_code == 403:
        raise PermissionError(
            f"403 Forbidden — check FOOTBALL_DATA_API_KEY or subscription tier.\n"
            f"URL: {url}"
        )
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    return resp.json()


# ── DB writers (Bronze: ON CONFLICT DO NOTHING) ───────────────────────────────

def write_competition(cur, comp: dict, code: str) -> None:
    cur.execute(
        """
        INSERT INTO euro_raw.competitions
            (competition_id, competition_name, competition_code,
             country, confederation, tier, format, data_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (competition_id) DO NOTHING
        """,
        (
            f"fdorg_{comp.get('id', code)}",
            comp.get("name", ""),
            code,
            comp.get("area", {}).get("name", ""),
            "UEFA",
            1,
            "round_robin",
            "football-data.org",
        ),
    )


def write_clubs(cur, teams: list, competition_id: str) -> None:
    if not teams:
        return
    rows = [
        (
            f"fdorg_{t['id']}",
            t.get("name", ""),
            t.get("shortName") or t.get("name", ""),
            t.get("tla") or "",
            competition_id,
            None,
            None,
            None,
            "football-data.org",
            str(t["id"]),
        )
        for t in teams
        if t.get("id")
    ]
    if not rows:
        return
    execute_values(
        cur,
        """
        INSERT INTO euro_raw.clubs
            (club_id, club_name, club_short_name, club_tla, competition_id,
             country, venue_id, founded_year, data_source, source_club_id)
        VALUES %s
        ON CONFLICT (club_id) DO NOTHING
        """,
        rows,
    )


def write_matches(cur, matches: list, competition_id: str, season_str: str) -> int:
    if not matches:
        return 0

    rows = []
    for m in matches:
        score = m.get("score") or {}
        ft    = score.get("fullTime") or {}
        ht    = score.get("halfTime") or {}
        home  = m.get("homeTeam") or {}
        away  = m.get("awayTeam") or {}

        rows.append((
            f"fdorg_{m['id']}",
            season_str,
            competition_id,
            m.get("matchday"),
            m.get("utcDate"),
            m.get("status"),
            f"fdorg_{home['id']}" if home.get("id") else None,
            f"fdorg_{away['id']}" if away.get("id") else None,
            ft.get("home"),
            ft.get("away"),
            ht.get("home"),
            ht.get("away"),
            score.get("winner"),
            m.get("stage"),
            str(m["id"]),
        ))

    execute_values(
        cur,
        """
        INSERT INTO euro_raw.fdorg_matches
            (match_id, season, competition_id, matchweek, date, status,
             home_club_id, away_club_id, home_goals, away_goals,
             home_goals_ht, away_goals_ht, winner, stage,
             data_source, source_match_id)
        VALUES %s
        ON CONFLICT (match_id) DO NOTHING
        """,
        rows,
        template=(
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
            "'football-data.org',%s)"
        ),
    )
    return len(rows)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Loading .env from: %s (exists=%s)", _ENV_PATH, _ENV_PATH.exists())

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FOOTBALL_DATA_API_KEY is not set.\n"
            f"Looked for .env at: {_ENV_PATH}\n"
            f"File exists: {_ENV_PATH.exists()}"
        )

    log.info("Connecting to Postgres...")
    conn = get_db_conn()
    conn.autocommit = False
    log.info("Connected.")
    log.info("Seasons : %s", [season_label(y) for y in SEASONS])
    log.info("Comps   : %s", list(COMPETITIONS.keys()))
    log.info("")

    total_attempted = 0
    errors = []

    try:
        for code, name in COMPETITIONS.items():
            for season_year in SEASONS:
                label = season_label(season_year)
                log.info("── %s  %s  (season=%d) ──", name, label, season_year)

                try:
                    payload = fdorg_get(
                        f"/competitions/{code}/matches",
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

                matches        = payload.get("matches") or []
                comp_meta      = payload.get("competition") or {}
                competition_id = f"fdorg_{comp_meta.get('id', code)}"

                teams_by_id = {}
                for m in matches:
                    for side in ("homeTeam", "awayTeam"):
                        t = m.get(side) or {}
                        if t.get("id"):
                            teams_by_id[t["id"]] = t

                with conn.cursor() as cur:
                    write_competition(cur, comp_meta, code)
                    write_clubs(cur, list(teams_by_id.values()), competition_id)
                    n = write_matches(cur, matches, competition_id, label)
                    total_attempted += n

                conn.commit()
                log.info(
                    "  ✓  %d match rows attempted  |  %d clubs  |  committed",
                    n, len(teams_by_id),
                )

    except Exception:
        conn.rollback()
        log.error("Rolled back on unhandled exception.")
        raise
    finally:
        conn.close()

    log.info("")
    log.info("═" * 60)
    log.info("Done. %d total match rows attempted.", total_attempted)
    if errors:
        log.warning("%d batch(es) failed:", len(errors))
        for e in errors:
            log.warning("  • %s", e)
    log.info("═" * 60)


if __name__ == "__main__":
    main()