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
            
            # User Metrics Table (Singleton-ish, keyed by date mostly or just latest)
            # For simplicity, let's keep a history of settings changes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_metrics (
                    date DATE PRIMARY KEY, 
                    lthr_bpm INTEGER,
                    vo2_max_cycling REAL,
                    vo2_max_running REAL,
                    last_updated TIMESTAMP
                )
            ''')

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def upsert_user_metrics(self, data):
        """
        Upsert user metrics. 
        Data should include: date, lthr_bpm, vo2_max_cycling, etc.
        """
        self._upsert('user_metrics', 'date', data)

    def get_latest_user_metrics(self):
        """Get the most recent user metrics."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT lthr_bpm, vo2_max_cycling FROM user_metrics ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return {'lthr_bpm': row[0], 'vo2_max_cycling': row[1]}
            return None
        except Exception as e:
            logger.error(f"Error fetching latest metrics: {e}")
            return None

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
            return None
        except Exception as e:
            logger.error(f"Error fetching details for {activity_id}: {e}")
            return None

    def get_recent_activity_ids(self, days=60, activity_types=None):
        """
        Get list of activity IDs for the last N days.
        args:
            days (int): Lookback period.
            activity_types (list): Optional list of activity types to filter by (e.g., ['cycling', 'virtual_ride']).
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if activity_types:
                # Format for IN clause
                placeholders = ', '.join(['%s'] * len(activity_types))
                query = f"""
                    SELECT activity_id 
                    FROM activities 
                    WHERE start_time >= NOW() - INTERVAL '%s days'
                    AND activity_type IN ({placeholders})
                    ORDER BY start_time DESC
                """
                params = [days] + activity_types
                cursor.execute(query, tuple(params))
            else:
                query = """
                    SELECT activity_id 
                    FROM activities 
                    WHERE start_time >= NOW() - INTERVAL '%s days'
                    ORDER BY start_time DESC
                """
                cursor.execute(query, (days,))
                
            results = [row[0] for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error fetching recent activities: {e}")
            return []

    def get_max_heart_rate(self, days=180):
        """Get the absolute maximum heart rate recorded in activities over the last N days."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = "SELECT MAX(max_hr) FROM activities WHERE start_time >= NOW() - INTERVAL '%s days'"
            cursor.execute(query, (days,))
            result = cursor.fetchone()
            conn.close()
            if result and result[0]:
                return int(result[0])
            return None # Fallback or None
        except Exception as e:
            logger.error(f"Error fetching max HR: {e}")
            return None

