import os
import json
from garminconnect import Garmin
from dotenv import load_dotenv
from datetime import date

load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

def display_json(data, label):
    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2))

try:
    print(f"Authenticating as {email}...")
    client = Garmin(email, password)
    client.login()
    print("Authentication successful.")

    today = date.today()
    
    # Fetch various data points to see what we want to store
    stats = client.get_user_summary(today.isoformat())
    with open("sample_summary.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    try:
        sleep = client.get_sleep_data(today.isoformat())
        with open("sample_sleep.json", "w") as f:
            json.dump(sleep, f, indent=2)
    except Exception as e:
        print(f"Error fetching sleep: {e}")

    try:
        # HRV is often in daily summary or separate. Let's check if there is a specific method.
        # Based on common knowledge of this lib, it might be get_hrv_data or similar.
        # Let's try to find it or just look at summary which often has nightly HRV.
        hrv = client.get_hrv_data(today.isoformat())
        with open("sample_hrv.json", "w") as f:
            json.dump(hrv, f, indent=2)
    except Exception as e:
        print(f"Error fetching HRV: {e}")

    try:
        activities = client.get_activities(0, 5) # Get last 5 activities
        with open("sample_activities.json", "w") as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        print(f"Error fetching activities: {e}")

    print("Saved sample data files")

    # heart_rates = client.get_heart_rates(today.isoformat())
    # display_json(heart_rates, "Heart Rates")

    # sleep = client.get_sleep_data(today.isoformat())
    # display_json(sleep, "Sleep Data")

except Exception as e:
    print(f"Error: {e}")
