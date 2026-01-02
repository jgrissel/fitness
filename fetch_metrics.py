from garmin_client import GarminClient
from db_manager import DBManager
from datetime import date
import logging

# Configure basic logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    print("Initializing Client & DB...")
    client = GarminClient()
    if not client.login():
        print("Login failed.")
        return

    db = DBManager()
    
    print("Fetching User Settings...")
    settings = client.get_user_settings()
    
    if settings:
        print(f"Found settings: {settings}")
        # Add date for storage
        data = {
            'date': date.today(),
            'lthr_bpm': settings.get('lthr'),
            'vo2_max_cycling': settings.get('vo2_max_cycling'),
            'vo2_max_running': settings.get('vo2_max_running')
        }
        db.upsert_user_metrics(data)
        print("Initial User Metrics saved to DB.")
    else:
        print("Could not fetch settings.")

if __name__ == "__main__":
    main()
