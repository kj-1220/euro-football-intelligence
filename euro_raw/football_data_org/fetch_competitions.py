import psycopg2
import os
from client import get
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

CONN = os.getenv("POSTGRES_URL",
    "host=127.0.0.1 port=5456 dbname=postgres user=postgres password=postgres")

# Competitions in scope with their football-data.org codes
COMPETITIONS = {
    "PL":  {"name": "Premier League",  "country": "England"},
    "PD":  {"name": "La Liga",         "country": "Spain"},
    "BL1": {"name": "Bundesliga",      "country": "Germany"},
    "SA":  {"name": "Serie A",         "country": "Italy"},
    "FL1": {"name": "Ligue 1",         "country": "France"},
    "CL":  {"name": "Champions League","country": "Europe"},
}

def upsert_competitions(cur):
    print("Seeding competitions...")
    for code, meta in COMPETITIONS.items():
        cur.execute("""
            INSERT INTO euro_raw.competitions
                (competition_id, competition_name, competition_code,
                 country, confederation, tier, data_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (competition_id) DO UPDATE SET
                competition_name = EXCLUDED.competition_name,
                competition_code = EXCLUDED.competition_code
        """, (
            code,
            meta["name"],
            code,
            meta["country"],
            "UEFA",
            1 if code != "CL" else None,
            "football-data.org"
        ))
    print(f"  {len(COMPETITIONS)} competitions seeded")

def fetch_and_upsert_clubs(cur):
    print("Fetching clubs per competition...")
    total = 0
    for code in COMPETITIONS:
        print(f"  Fetching {code}...")
        data = get(f"/competitions/{code}/teams")
        teams = data.get("teams", [])

        for team in teams:
            venue_id = None
            if team.get("venue"):
                venue_id = f"venue_{team['id']}"
                cur.execute("""
                    INSERT INTO euro_raw.venues
                        (venue_id, venue_name, city, country, data_source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (venue_id) DO NOTHING
                """, (
                    venue_id,
                    team.get("venue"),
                    team.get("address", "").split(",")[-1].strip() if team.get("address") else None,
                    team.get("area", {}).get("name"),
                    "football-data.org"
                ))

            cur.execute("""
                INSERT INTO euro_raw.clubs
                    (club_id, club_name, club_short_name, club_tla,
                     competition_id, country, venue_id,
                     founded_year, data_source, source_club_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (club_id) DO UPDATE SET
                    club_name = EXCLUDED.club_name,
                    club_tla  = EXCLUDED.club_tla
            """, (
                f"fdorg_{team['id']}",
                team.get("name"),
                team.get("shortName"),
                team.get("tla"),
                code,
                team.get("area", {}).get("name"),
                venue_id,
                team.get("founded"),
                "football-data.org",
                str(team["id"])
            ))
            total += 1

    print(f"  {total} clubs upserted")

def run():
    conn = psycopg2.connect(CONN)
    cur = conn.cursor()
    upsert_competitions(cur)
    fetch_and_upsert_clubs(cur)
    conn.commit()
    cur.close()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    run()
