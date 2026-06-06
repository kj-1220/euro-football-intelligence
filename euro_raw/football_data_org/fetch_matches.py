import psycopg2
import os
from client import get
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

CONN = os.getenv("POSTGRES_URL",
    "host=127.0.0.1 port=5456 dbname=postgres user=postgres password=postgres")

COMPETITIONS = ["PL", "PD", "BL1", "SA", "FL1", "CL"]

# Seasons to fetch — Tier A goes back as far as available
# football-data.org free tier supports from 2000 onward for most leagues
SEASONS = [2023, 2024]

def upsert_match(cur, match, competition_id):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    score = match.get("score", {})
    full  = score.get("fullTime", {})
    half  = score.get("halfTime", {})

    cur.execute("""
        INSERT INTO euro_raw.fdorg_matches (
            match_id, season, competition_id, matchweek,
            date, status,
            home_club_id, away_club_id,
            home_goals, away_goals,
            home_goals_ht, away_goals_ht,
            winner, stage,
            source_match_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (match_id) DO NOTHING
    """, (
        f"fdorg_{match['id']}",
        str(match.get("season", {}).get("startDate", "")[:4]),
        competition_id,
        match.get("matchday"),
        match.get("utcDate"),
        match.get("status"),
        f"fdorg_{home['id']}" if home.get("id") else None,
        f"fdorg_{away['id']}" if away.get("id") else None,
        full.get("home"),
        full.get("away"),
        half.get("home"),
        half.get("away"),
        score.get("winner"),
        match.get("stage"),
        str(match["id"])
    ))

def fetch_matches(cur, competition_id, season):
    print(f"  {competition_id} {season}...")
    try:
        data = get(f"/competitions/{competition_id}/matches",
                   params={"season": season})
        matches = data.get("matches", [])
        count = 0
        for match in matches:
            upsert_match(cur, match, competition_id)
            count += 1
        print(f"    {count} matches")
        return count
    except Exception as e:
        print(f"    Error: {e}")
        return 0

def run():
    conn = psycopg2.connect(CONN)
    cur = conn.cursor()
    total = 0

    for comp in COMPETITIONS:
        print(f"\nFetching {comp}...")
        for season in SEASONS:
            n = fetch_matches(cur, comp, season)
            total += n
            conn.commit()  # commit per season so progress is saved

    cur.close()
    conn.close()
    print(f"\nTotal matches inserted: {total}")
    print("Done.")

if __name__ == "__main__":
    run()
