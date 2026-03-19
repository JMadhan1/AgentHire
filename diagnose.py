
import os
import requests
import sqlite3
from dotenv import load_dotenv

def check_env():
    print("--- 1. Checking .env file ---")
    load_dotenv()
    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        print("[FAIL] TINYFISH_API_KEY not found in .env")
    elif api_key.startswith("your_"):
        print("[FAIL] TINYFISH_API_KEY is still the placeholder")
    else:
        print(f"[OK] API Key found: {api_key[:10]}...")

def check_db():
    print("\n--- 2. Checking Database ---")
    db_path = 'instance/agenthire.db'
    if not os.path.exists(db_path):
        print(f"[FAIL] Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM applications")
    count = cursor.fetchone()[0]
    print(f"[OK] Database connected. Total applications: {count}")
    
    cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
    stats = cursor.fetchall()
    for s, c in stats:
        print(f"  - {s}: {c}")
    conn.close()

def check_api_connectivity():
    print("\n--- 3. Checking TinyFish API Connectivity ---")
    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key: return
    
    try:
        url = "https://agent.tinyfish.ai/v1/automation/run-sse"
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        payload = {"url": "https://example.com", "goal": "Verify API", "browser_profile": "stealth"}
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=10)
        if response.status_code == 200:
            print("[OK] TinyFish API responded successfully.")
        else:
            print(f"[FAIL] TinyFish API returned HTTP {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")

def check_localhost_issue():
    print("\n--- 4. Localhost Warning ---")
    print("NOTE: If you are running on localhost, the AI agent CANNOT download your resume.")
    print("To fix this, you MUST use a tunnel:")
    print("  npx tinyfi.sh 5000")
    print("  OR")
    print("  ngrok http 5000")
    print("Then access your app via the public URL provided by the tunnel.")

if __name__ == "__main__":
    check_env()
    check_db()
    check_api_connectivity()
    check_localhost_issue()
