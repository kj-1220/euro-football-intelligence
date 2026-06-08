#!/usr/bin/env python3
"""
scripts/check_api_coverage.py

Probes football-data.org to find the earliest available season
for each Phase 1 competition across matches and standings endpoints.

Run this once to determine how far back to set SEASONS in ingestion scripts.
"""

from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPO_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

COMPETITIONS = {
    "PL":  "Premier League",
    "PD":  "La Liga",
    "BL1": "Bundesliga",
    "SA":  "Serie A",
    "FL1": "Ligue 1",
}

BASE_URL    = "https://api.football-data.org/v4"
DELAY       = 7
PROBE_START = 2000  # earliest year to probe
PROBE_END   = 2022  # we already know 2023-2025 work


def get(path: str, api_key: str, params: dict = None) -> tuple[int, dict]:
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers={"X-Auth-Token": api_key},
        params=params or {},
        timeout=30,
    )
    time.sleep(DELAY)
    return resp.status_code, resp.json() if resp.ok else {}


def main() -> None:
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise EnvironmentError("FOOTBALL_DATA_API_KEY not set")

    log.info("Probing seasons %d-%d for each competition", PROBE_START, PROBE_END)
    log.info("Delay: %ds per request  |  estimated time: ~%ds total\n",
             DELAY, DELAY * len(COMPETITIONS) * (PROBE_END - PROBE_START + 1) * 2)

    results = {}

    for code, name in COMPETITIONS.items():
        log.info("══ %s (%s) ══", name, code)
        earliest_matches   = None
        earliest_standings = None

        for year in range(PROBE_START, PROBE_END + 1):
            # --- matches ---
            status, data = get(f"/competitions/{code}/matches", api_key, {"season": year})
            count = len(data.get("matches", []))
            if status == 200 and count > 0:
                if earliest_matches is None:
                    earliest_matches = year
                log.info("  matches    season=%d  status=%d  matches=%d", year, status, count)
            else:
                log.info("  matches    season=%d  status=%d  (no data)", year, status)

            # --- standings ---
            status2, data2 = get(f"/competitions/{code}/standings", api_key, {"season": year})
            tables = data2.get("standings", [])
            total  = next((t for t in tables if t.get("type") == "TOTAL"), None)
            rows   = len(total.get("table", [])) if total else 0
            if status2 == 200 and rows > 0:
                if earliest_standings is None:
                    earliest_standings = year
                log.info("  standings  season=%d  status=%d  rows=%d", year, status2, rows)
            else:
                log.info("  standings  season=%d  status=%d  (no data)", year, status2)

        results[code] = {
            "earliest_matches":   earliest_matches,
            "earliest_standings": earliest_standings,
        }
        log.info("")

    log.info("═" * 60)
    log.info("SUMMARY")
    log.info("═" * 60)
    log.info("%-6s  %-20s  %-18s  %-18s", "Code", "Name", "Matches from", "Standings from")
    log.info("%-6s  %-20s  %-18s  %-18s", "─"*6, "─"*20, "─"*18, "─"*18)
    for code, name in COMPETITIONS.items():
        r = results[code]
        log.info(
            "%-6s  %-20s  %-18s  %-18s",
            code, name,
            str(r["earliest_matches"]),
            str(r["earliest_standings"]),
        )
    log.info("═" * 60)


if __name__ == "__main__":
    main()