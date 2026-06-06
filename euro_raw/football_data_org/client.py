import requests
import time
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

BASE_URL = "https://api.football-data.org/v4"
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
DELAY = float(os.getenv("FDORG_DELAY_SECONDS", 6))  # free tier: 10 req/min

def get(endpoint, params=None):
    """Make a rate-limited request to football-data.org"""
    headers = {"X-Auth-Token": API_KEY}
    url = f"{BASE_URL}{endpoint}"
    
    time.sleep(DELAY)
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    if response.status_code == 429:
        print("  Rate limited — waiting 60 seconds...")
        time.sleep(60)
        response = requests.get(url, headers=headers, params=params, timeout=30)
    
    response.raise_for_status()
    return response.json()
