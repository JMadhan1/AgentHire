
import os
from app import create_app
from models import db, Application

def dump_log(app_id):
    app = create_app()
    with app.app_context():
        app_record = Application.query.get(app_id)
        if app_record and app_record.agent_log:
            with open(f'log_{app_id}.txt', 'w', encoding='utf-8') as f:
                f.write(app_record.agent_log)
            print(f"Log written to log_{app_id}.txt")
        else:
            print("Log not found.")

if __name__ == "__main__":
    dump_log(9)
