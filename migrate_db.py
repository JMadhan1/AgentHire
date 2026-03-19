
import sqlite3
import os

db_path = 'instance/agenthire.db'

if os.path.exists(db_path):
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking if 'resume_path' column exists in 'applications' table...")
        cursor.execute("PRAGMA table_info(applications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'resume_path' not in columns:
            print("Adding 'resume_path' column to 'applications' table...")
            cursor.execute("ALTER TABLE applications ADD COLUMN resume_path VARCHAR(500)")
            conn.commit()
            print("Successfully added 'resume_path' column.")
        else:
            print("'resume_path' column already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database file not found at {db_path}")
