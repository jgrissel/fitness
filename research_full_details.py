
import os
import logging
import json
from garminconnect import Garmin
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def research_details():
    load_dotenv()
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    
    if not email or not password:
        logger.error("Missing credentials in .env")
        return

    try:
        client = Garmin(email, password)
        client.login()
        logger.info("Login successful.")
        
        # Get one recent activity
        activities = client.get_activities(0, 1)
        if not activities:
            logger.info("No activities found.")
            return

        act_id = activities[0]['activityId']
        logger.info(f"Fetching details for activity {act_id}...")
        
        # Fetch full details
        details = client.get_activity_details(act_id)
        
        if details:
            with open("activity_details_dump.json", "w") as f:
                json.dump(details, f, indent=4)
            logger.info("Dumped details to activity_details_dump.json")
            
        # Also check if there are other granular endpoints?
        # spltis, etc are usually in details.
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    research_details()
