
import sqlite3
import os
from datetime import datetime

db_path = r'c:\Users\jmadh\OneDrive\Desktop\Agent_hire\agenthire\instance\agenthire.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, job_url, status, error_msg, created_at FROM applications ORDER BY id DESC LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"URL: {row[1]}")
    print(f"Status: {row[2]}")
    print(f"Error: {row[3]}")
    print(f"Created At: {row[4]}")
    print("-" * 20)

conn.close()
