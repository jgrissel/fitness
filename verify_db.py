import sqlite3
import pandas as pd

conn = sqlite3.connect("garmin_data.db")

print("--- Daily Summary ---")
print(pd.read_sql_query("SELECT * FROM daily_summary", conn))

print("\n--- Sleep Summary ---")
print(pd.read_sql_query("SELECT * FROM sleep_summary", conn))

print("\n--- HRV Summary ---")
print(pd.read_sql_query("SELECT * FROM hrv_summary", conn))

print("\n--- Activities ---")
print(pd.read_sql_query("SELECT activity_id, activity_name, start_time, distance_meters FROM activities", conn))

conn.close()
