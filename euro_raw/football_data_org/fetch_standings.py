import psycopg2
import os
from client import get
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

CONN = os.getenv("POSTGRES_URL",
    "host=127.0.0.1 port=5456 dbname=postgres user=postgres password=postgres")

COMPETITIONS = ["PL", "PD", "BL1", "SA", "FL1"]
SEASONS = [2023, 2024]

def fetch_standings(cur, competition_id, season):
    print(f"  {competition_id} {season}...")
    try:
        data = get(f"/competitions/{competition_id}/standings",
                   params={"season": season})
        standings = data.get("standings", [])
        count = 0

        for standing_group in standings:
            if standing_group.get("type") != "TOTAL":
                continue
            for entry in standing_group.get("table", []):
                team = entry.get("team", {})
                cur.execute("""
                    INSERT INTO euro_raw.fdorg_standings (
                        season, competition_id, matchweek,
                        club_id, position,
                        played, won, drawn, lost,
                        goals_for, goals_against, goal_difference,
                        points, form
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    str(season),
                    competition_id,
                    data.get("season", {}).get("currentMatchday"),
                    f"fdorg_{team['id']}" if team.get("id") else None,
                    entry.get("position"),
                    entry.get("playedGames"),
                    entry.get("won"),
                    entry.get("draw"),
                    entry.get("lost"),
                    entry.get("goalsFor"),
                    entry.get("goalsAgainst"),
                    entry.get("goalDifference"),
                    entry.get("points"),
                    entry.get("form")
                ))
                count += 1
        print(f"    {count} entries")
        return count
    except Exception as e:
        print(f"    Error: {e}")
        return 0

def run():
    conn = psycopg2.connect(CONN)
    cur = conn.cursor()
    total = 0

    for comp in COMPETITIONS:
        print(f"\nFetching standings for {comp}...")
        for season in SEASONS:
            n = fetch_standings(cur, comp, season)
            total += n
            conn.commit()

    cur.close()
    conn.close()
    print(f"\nTotal standing entries inserted: {total}")
    print("Done.")

if __name__ == "__main__":
    run()
