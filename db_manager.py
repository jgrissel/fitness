import os
import json
import logging
import psycopg2
from psycopg2.extras import Json
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.dbname = os.getenv("DB_NAME", "garmin")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
        self.init_db()

    def get_connection(self):
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def init_db(self):
        """Initialize database schema."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Daily Summary Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summary (
                    date DATE PRIMARY KEY,
                    total_steps INTEGER,
                    total_distance_meters INTEGER,
                    active_kcal REAL,
                    bmr_kcal REAL,
                    total_kcal REAL,
                    resting_hr INTEGER,
                    min_hr INTEGER,
                    max_hr INTEGER,
                    avg_stress INTEGER,
                    max_stress INTEGER,
                    body_battery_current INTEGER,
                    body_battery_high INTEGER,
                    body_battery_low INTEGER,
                    last_updated TIMESTAMP
                )
            ''')

            # Sleep Summary Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sleep_summary (
                    date DATE PRIMARY KEY,
                    total_sleep_seconds INTEGER,
                    deep_sleep_seconds INTEGER,
                    light_sleep_seconds INTEGER,
                    rem_sleep_seconds INTEGER,
                    awake_sleep_seconds INTEGER,
                    sleep_score INTEGER,
                    sleep_quality TEXT,
                    last_updated TIMESTAMP
                )
            ''')

            # HRV Summary Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hrv_summary (
                    date DATE PRIMARY KEY,
                    last_night_avg INTEGER,
                    weekly_avg INTEGER,
                    status TEXT,
                    last_updated TIMESTAMP
                )
            ''')

            # Activities Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id BIGINT PRIMARY KEY,
                    activity_name TEXT,
                    activity_type TEXT,
                    start_time TIMESTAMP,
                    distance_meters REAL,
                    duration_seconds REAL,
                    avg_hr INTEGER,
                    max_hr INTEGER,
                    calories REAL,
                    avg_power INTEGER,
                    max_power INTEGER,
                    elevation_gain_meters REAL,
                    elevation_loss_meters REAL,
                    avg_cadence INTEGER,
                    max_cadence INTEGER,
                    steps INTEGER,
                    last_updated TIMESTAMP
                )
            ''')

            # Activity Details Table (Full JSON store)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_details (
                    activity_id BIGINT PRIMARY KEY REFERENCES activities(activity_id),
                    details JSONB,
                    last_updated TIMESTAMP
                )
            ''')

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def upsert_daily_summary(self, data):
        self._upsert('daily_summary', 'date', data)

    def upsert_sleep_summary(self, data):
        self._upsert('sleep_summary', 'date', data)

    def upsert_hrv_summary(self, data):
        self._upsert('hrv_summary', 'date', data)

    def upsert_activity(self, data):
        self._upsert('activities', 'activity_id', data)

    def upsert_activity_details(self, activity_id, details):
        data = {
            'activity_id': activity_id,
            'details': Json(details),
            'last_updated': datetime.now()
        }
        self._upsert('activity_details', 'activity_id', data)

    def _upsert(self, table, conflict_key, data):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Add timestamp if missing
            if 'last_updated' not in data:
                data['last_updated'] = datetime.now()

            keys = list(data.keys())
            columns = ', '.join(keys)
            placeholders = ', '.join(['%s'] * len(keys))
            updates = ', '.join([f"{k}=EXCLUDED.{k}" for k in keys if k != conflict_key])
            
            query = f'''
                INSERT INTO {table} ({columns})
                VALUES ({placeholders})
                ON CONFLICT ({conflict_key}) 
                DO UPDATE SET {updates}
            '''
            
            cursor.execute(query, list(data.values()))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error upserting into {table}: {e}")

    def get_activity_details_json(self, activity_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT details FROM activity_details WHERE activity_id = %s", (activity_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching details for {activity_id}: {e}")
            return None

