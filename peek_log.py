
import os
import json
from app import create_app
from models import db, Application

def peek_log(app_id):
    app = create_app()
    with app.app_context():
        app_record = Application.query.get(app_id)
        if not app_record:
            print(f"Application {app_id} not found.")
            return
        
        print(f"--- Application {app_id} Details ---")
        print(f"Status: {app_record.status}")
        print(f"Error Message: {app_record.error_msg}")
        
        if app_record.agent_log:
            lines = [line.strip() for line in app_record.agent_log.split('\n') if line.strip()]
            for line in lines:
                try:
                    data = json.loads(line)
                    if data.get('type') in ('COMPLETE', 'COMPLETED'):
                        result = data.get('resultJson') or data.get('result') or data.get('output') or {}
                        if isinstance(result, str):
                            result = json.loads(result)
                        print(f"BLOCKER: {result.get('blockers')}")
                except Exception as e:
                    pass
        else:
            print("No logs found.")

if __name__ == "__main__":
    peek_log(9)
