import fetch_competitions
import fetch_matches
import fetch_standings
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

CONN = os.getenv("POSTGRES_URL",
    "host=127.0.0.1 port=5456 dbname=postgres user=postgres password=postgres")

if __name__ == "__main__":
    conn = psycopg2.connect(CONN)
    cur = conn.cursor()

    print("=== Step 1: Competitions + Clubs ===")
    fetch_competitions.run()

    print("\n=== Step 2: Matches ===")
    fetch_matches.run()

    print("\n=== Step 3: Standings ===")
    fetch_standings.run()

    print("\n=== All done ===")
