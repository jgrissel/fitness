import time
import schedule
import logging
import argparse
from datetime import date
from garmin_client import GarminClient
from db_manager import DBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("garmin_logger.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_extraction():
    logger.info("Starting data extraction job...")
    
    try:
        client = GarminClient()
        if not client.login():
            logger.error("Login failed. Aborting job.")
            return

        db = DBManager()
        today = date.today()
        
        # 1. Daily Summary
        logger.info(f"Fetching daily summary for {today}...")
        summary = client.get_daily_summary(today)
        if summary:
            db.upsert_daily_summary(summary)
            logger.info("Daily summary saved.")
        
        # 2. Sleep Data
        logger.info(f"Fetching sleep data for {today}...")
        sleep = client.get_sleep_data(today)
        if sleep:
            db.upsert_sleep_summary(sleep)
            logger.info("Sleep data saved.")

        # 3. HRV Data
        logger.info(f"Fetching HRV data for {today}...")
        hrv = client.get_hrv_data(today)
        if hrv:
            db.upsert_hrv_summary(hrv)
            logger.info("HRV data saved.")

        # 4. Activities
        logger.info("Fetching recent activities...")
        activities = client.get_activities(limit=5) # Fetch last 5 to ensure we catch recent ones
        count = 0
        for act in activities:
            db.upsert_activity(act)
            
            # Fetch full details
            act_id = act.get('activity_id')
            if act_id:
                logger.info(f"Fetching full details for activity {act_id}...")
                details = client.get_activity_details(act_id)
                if details:
                    db.upsert_activity_details(act_id, details)
            
            count += 1
        logger.info(f"Saved {count} activities.")

        logger.info("Data extraction job completed successfully.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during extraction: {e}")

def main():
    parser = argparse.ArgumentParser(description="Garmin Health Data Logger")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    if args.once:
        run_extraction()
    else:
        logger.info("Starting scheduler. Job will run every hour.")
        # Run once immediately on startup
        run_extraction()
        
        # Schedule every hour
        schedule.every().hour.do(run_extraction)
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
