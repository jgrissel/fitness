import os
from garminconnect import Garmin
from dotenv import load_dotenv

# Load env from .env file if present
load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

if not email or not password:
    email = input("Enter Garmin Email: ")
    password = input("Enter Garmin Password: ")

print(f"Attempting login for {email}...")

try:
    client = Garmin(email, password)
    client.login()
    
    output_path = "garmin_tokens"
    client.garth.dump(output_path)
    
    print("\nSUCCESS! Login verified.")
    print(f"Tokens saved to directory: '{output_path}'")
    print("\nNow, upload this folder (or its contents) to your VPS at '/home/deploy/containers/fitness/garmin_tokens'.")
    print("Wait, simpler: The docker container maps data volume.")
    print("\nCORRECT STEPS:")
    print("1. This script created a folder named 'garmin_tokens'.")
    print("2. You need to copy this folder to your VPS so the container can see it.")
    print("   Since the container expects '/data/garmin_tokens', and '/data' is a volume...")
    print("   Actually, looking at the code, it expects a directory path.")
    
except Exception as e:
    print(f"\nLOGIN FAILED: {e}")
    if "401" in str(e):
        print("Check your email/password.")
    else:
        print("Are you running this locally? If on VPS, try running locally.")
