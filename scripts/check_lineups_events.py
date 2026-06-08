#!/usr/bin/env python3
"""
scripts/check_lineups_events.py

Fetches one match from football-data.org and prints the raw lineups
and events response structure so we know exactly what fields are available
before writing ingestion scripts.
"""

from __future__ import annotations

import os
import sys
import json
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

BASE_URL = "https://api.football-data.org/v4"
DELAY    = 7


def get(path: str, api_key: str, params: dict = None) -> dict:
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers={"X-Auth-Token": api_key},
        params=params or {},
        timeout=30,
    )
    time.sleep(DELAY)
    if not resp.ok:
        log.error("HTTP %d: %s", resp.status_code, resp.text[:200])
        return {}
    return resp.json()


def main() -> None:
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise EnvironmentError("FOOTBALL_DATA_API_KEY not set")

    # Step 1: get one finished PL match from 2023-24
    log.info("Fetching one finished PL match from 2023-24...")
    data = get("/competitions/PL/matches", api_key, {"season": 2023, "status": "FINISHED"})
    matches = data.get("matches", [])
    if not matches:
        log.error("No matches returned")
        sys.exit(1)

    match = matches[0]
    match_id = match["id"]
    log.info("Using match_id=%d  (%s vs %s)",
             match_id,
             match["homeTeam"]["name"],
             match["awayTeam"]["name"])
    time.sleep(DELAY)

    # Step 2: fetch that match directly — lineups and events live on /matches/{id}
    log.info("Fetching /matches/%d ...", match_id)
    detail = get(f"/matches/{match_id}", api_key)

    log.info("\n── RAW MATCH DETAIL ──────────────────────────────────")
    print(json.dumps(detail, indent=2))


if __name__ == "__main__":
    main()