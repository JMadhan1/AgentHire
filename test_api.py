
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TINYFISH_API_KEY")

if not api_key:
    print("No API key found in .env")
    exit(1)

print(f"Testing API key: {api_key[:10]}...")

url = "https://agent.tinyfish.ai/v1/automation/run-sse"
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}
payload = {
    "url": "https://example.com",
    "goal": "Verify page title",
    "browser_profile": "stealth",
}

try:
    response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
    if response.status_code == 200:
        print("Success! API key is valid.")
        # Read just the first event
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data:"):
                print(f"Received event: {line}")
                break
    else:
        print(f"Failed! Status code: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error checking API: {e}")
