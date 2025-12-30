
import json
import pandas as pd
from activity_parser import parse_activity_details

def test_parser():
    try:
        with open("activity_details_dump.json", "r") as f:
            data = json.load(f)
            
        df = parse_activity_details(data)
        print("DataFrame Shape:", df.shape)
        print("Columns:", df.columns.tolist())
        print("\nFirst 5 rows:")
        print(df.head())
        
        # Check for expected columns
        expected = ['heart_rate', 'speed', 'latitude', 'longitude']
        for col in expected:
            if col not in df.columns:
                print(f"WARNING: Expected column '{col}' not found.")
            else:
                print(f"Verified '{col}' exists.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_parser()
