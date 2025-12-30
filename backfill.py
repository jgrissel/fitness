import time
import logging
import argparse
import random
from datetime import date, timedelta, datetime
from garmin_client import GarminClient
from db_manager import DBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backfill.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def random_sleep(min_seconds=2, max_seconds=5):
    """Sleep for a random amount of time to be polite to the API."""
    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)

def backfill_data(start_date: date, end_date: date):
    logger.info(f"Starting backfill from {start_date} to {end_date}...")
    
    client = GarminClient()
    if not client.login():
        logger.error("Login failed. Aborting backfill.")
        return

    db = DBManager()
    
    # Iterate through each day
    current_date = start_date
    while current_date <= end_date:
        logger.info(f"Processing {current_date}...")
        
        try:
            # 1. Daily Summary
            summary = client.get_daily_summary(current_date)
            if summary:
                db.upsert_daily_summary(summary)
                logger.info(f"  - Daily summary saved.")
            else:
                logger.warning(f"  - No daily summary found.")
            random_sleep()

            # 2. Sleep Data
            sleep = client.get_sleep_data(current_date)
            if sleep:
                db.upsert_sleep_summary(sleep)
                logger.info(f"  - Sleep data saved.")
            else:
                logger.warning(f"  - No sleep data found.")
            random_sleep()

            # 3. HRV Data
            hrv = client.get_hrv_data(current_date)
            if hrv:
                db.upsert_hrv_summary(hrv)
                logger.info(f"  - HRV data saved.")
            else:
                logger.warning(f"  - No HRV data found.")
            random_sleep()

        except Exception as e:
            logger.error(f"Error processing {current_date}: {e}")
        
        current_date += timedelta(days=1)

    # 4. Activities
    # Activities are fetched by index, not strictly by date in the basic call, 
    # but we can fetch a large batch and filter, or just fetch by limit.
    # For backfill, it's often safer to just fetch a large number of recent activities
    # that covers the period.
    # A better approach for "year" backfill is to fetch by date range if the lib supports it,
    # or just paginate until we hit dates older than start_date.
    
    logger.info("Backfilling activities...")
    # We'll implement a pagination loop
    limit = 100
    start_index = 0
    keep_fetching = True
    
    while keep_fetching:
        logger.info(f"Fetching activities starting at index {start_index}...")
        activities = client.get_activities(start_index=start_index, limit=limit)
        
        if not activities:
            logger.info("No more activities found.")
            break
            
        count_in_range = 0
        for act in activities:
            # Parse activity start time
            # Format from API is usually 'YYYY-MM-DD HH:MM:SS'
            act_time_str = act['start_time']
            try:
                act_date = datetime.strptime(act_time_str, "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                # Fallback or skip if format is weird
                continue
                
            if act_date > end_date:
                continue # Too new, skip but keep going
            
            if act_date < start_date:
                # We've gone past the start date. 
                # Since activities are usually returned newest first, we can stop.
                logger.info(f"Reached activity date {act_date} which is older than start date {start_date}. Stopping activity fetch.")
                keep_fetching = False
                break
                
            # It's in range
            db.upsert_activity(act)
            
            # Fetch full details
            act_id = act.get('activity_id')
            if act_id:
                logger.info(f"    - Fetching full details for activity {act_id}...")
                details = client.get_activity_details(act_id)
                if details:
                    db.upsert_activity_details(act_id, details)
            
            count_in_range += 1
            
        logger.info(f"  - Saved {count_in_range} activities from this batch.")
        
        if keep_fetching:
            start_index += limit
            random_sleep()

    logger.info("Backfill completed.")

def main():
    parser = argparse.ArgumentParser(description="Garmin Data Backfill Tool")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        
        if start_date > end_date:
            print("Error: Start date must be before end date.")
            return
            
        backfill_data(start_date, end_date)
        
    except ValueError:
        print("Error: Invalid date format. Please use YYYY-MM-DD.")

if __name__ == "__main__":
    main()
