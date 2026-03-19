
import sqlite3
import os

db_path = r'c:\Users\jmadh\OneDrive\Desktop\Agent_hire\agenthire\instance\agenthire.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, full_name, resume_path FROM profiles")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"Name: {row[1]}")
    print(f"Resume Path: {row[2]}")
    print("-" * 20)

conn.close()
