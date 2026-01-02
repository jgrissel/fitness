import os
import json
import logging
from garminconnect import Garmin
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    token_path = "/data/garmin_tokens" # Using same path as client

    try:
        # Simplest login
        client = Garmin(email, password)
        client.login()
        
        print("Logged in.")
        
        # 1. Try to find user settings or profile
        # Often these libraries expose internal dicts or specific methods
        
        # Check standard profile
        # Note: garth (underlying lib) might be accessible via client.garth
        
        # Let's inspect what's available
        # client.get_audio_reports(...)
        # client.get_device_settings(...) 
        
        # Try fetching device settings (often contains HR zones)
        devices = client.get_devices()
        print(f"\nFound {len(devices)} devices.")
        if devices:
            dev_id = devices[0]['deviceId']
            print(f"Checking settings for device {dev_id}...")
            settings = client.get_device_settings(dev_id)
            with open("device_settings.json", "w") as f:
                 json.dump(settings, f, indent=2)
            print("Saved device_settings.json")
            
        # Try fetching user biometrics / settings
        # There isn't a documented single 'get_biometrics' 
        # but 'get_user_summary' has resting heart rate etc.
        # Max HR and LTHR are often in 'user-settings' or 'zones'
        
        # Let's try an undocumented endpoint via garth if possible, or standard methods
        # Standard: client.get_heart_rates(today) -> This is daily timeline
        
        # Check training status? 
        try:
             training_status = client.get_training_status(iso_date=None) # Latest
             print("\nTraining Status:")
             print(json.dumps(training_status, indent=2))
        except Exception as e:
            print(f"No training status: {e}")

        # The best bet for Max HR / LTHR is usually the User Profile or Heart Rate Zones
        # user_profile = client.get_user_profile() # Not a standard method name perhaps
        
        # Attempt to get HR zones (where Max HR and LTHR are usually defined)
        # client.get_heart_rate_zones() ?
        # inspecting dir(client) might be useful if we were interactive, but here we guess common names
        
        # Checking underlying garth client for profile
        # GET /userprofile-service/userprofile/user-settings
        if hasattr(client, 'garth'):
             print("\nFetch User Settings via Garth...")
             user_settings = client.garth.connectapi("/userprofile-service/userprofile/user-settings")
             with open("user_settings.json", "w") as f:
                 json.dump(user_settings, f, indent=2)
             print("Saved user_settings.json")
             
             # Also training zones?
             # GET /biometrictraining-service/heartRateZones
             zones = client.garth.connectapi("/biometrictraining-service/heartRateZones")
             with open("hr_zones.json", "w") as f:
                 json.dump(zones, f, indent=2)
             print("Saved hr_zones.json")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
