import requests
import psycopg2
import csv
import io
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

CONN = os.getenv("POSTGRES_URL", 
    "host=127.0.0.1 port=5456 dbname=postgres user=postgres password=postgres")

# ClubElo endpoint — returns full current ratings as CSV
URL = "http://api.clubelo.com/2025-06-06"

def fetch_and_load():
    print("Fetching ClubElo ratings...")
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    print(f"  {len(rows)} clubs returned")

    conn = psycopg2.connect(CONN)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for row in rows:
        # Skip if this club+date already exists
        cur.execute("""
            SELECT 1 FROM euro_raw.clubelo_ratings
            WHERE club_name = %s AND date = %s
        """, (row["Club"], row["From"]))

        if cur.fetchone():
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO euro_raw.clubelo_ratings
                (club_name, date, elo_rating, competition, rank)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            row["Club"],
            row["From"],
            float(row["Elo"]) if row["Elo"] else None,
            row["Country"],
            int(row["Rank"]) if row["Rank"] else None,
        ))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"  Inserted: {inserted} | Skipped (already exists): {skipped}")
    print("Done.")

if __name__ == "__main__":
    fetch_and_load()
