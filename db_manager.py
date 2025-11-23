import sqlite3
import os
from datetime import datetime

DB_NAME = os.getenv("DB_PATH", "garmin_data.db")

class DBManager:
    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else DB_NAME
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Daily Summary Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
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
                date TEXT PRIMARY KEY,
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
                date TEXT PRIMARY KEY,
                last_night_avg INTEGER,
                weekly_avg INTEGER,
                status TEXT,
                last_updated TIMESTAMP
            )
        ''')

        # Activities Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                activity_id INTEGER PRIMARY KEY,
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

        conn.commit()
        conn.close()

    def upsert_daily_summary(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            INSERT INTO daily_summary (
                date, total_steps, total_distance_meters, active_kcal, bmr_kcal, total_kcal,
                resting_hr, min_hr, max_hr, avg_stress, max_stress,
                body_battery_current, body_battery_high, body_battery_low, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_steps=excluded.total_steps,
                total_distance_meters=excluded.total_distance_meters,
                active_kcal=excluded.active_kcal,
                bmr_kcal=excluded.bmr_kcal,
                total_kcal=excluded.total_kcal,
                resting_hr=excluded.resting_hr,
                min_hr=excluded.min_hr,
                max_hr=excluded.max_hr,
                avg_stress=excluded.avg_stress,
                max_stress=excluded.max_stress,
                body_battery_current=excluded.body_battery_current,
                body_battery_high=excluded.body_battery_high,
                body_battery_low=excluded.body_battery_low,
                last_updated=excluded.last_updated
        '''
        
        cursor.execute(query, (
            data.get('date'),
            data.get('total_steps'),
            data.get('total_distance_meters'),
            data.get('active_kcal'),
            data.get('bmr_kcal'),
            data.get('total_kcal'),
            data.get('resting_hr'),
            data.get('min_hr'),
            data.get('max_hr'),
            data.get('avg_stress'),
            data.get('max_stress'),
            data.get('body_battery_current'),
            data.get('body_battery_high'),
            data.get('body_battery_low'),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()

    def upsert_sleep_summary(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            INSERT INTO sleep_summary (
                date, total_sleep_seconds, deep_sleep_seconds, light_sleep_seconds,
                rem_sleep_seconds, awake_sleep_seconds, sleep_score, sleep_quality, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_sleep_seconds=excluded.total_sleep_seconds,
                deep_sleep_seconds=excluded.deep_sleep_seconds,
                light_sleep_seconds=excluded.light_sleep_seconds,
                rem_sleep_seconds=excluded.rem_sleep_seconds,
                awake_sleep_seconds=excluded.awake_sleep_seconds,
                sleep_score=excluded.sleep_score,
                sleep_quality=excluded.sleep_quality,
                last_updated=excluded.last_updated
        '''
        
        cursor.execute(query, (
            data.get('date'),
            data.get('total_sleep_seconds'),
            data.get('deep_sleep_seconds'),
            data.get('light_sleep_seconds'),
            data.get('rem_sleep_seconds'),
            data.get('awake_sleep_seconds'),
            data.get('sleep_score'),
            data.get('sleep_quality'),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()

    def upsert_hrv_summary(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            INSERT INTO hrv_summary (
                date, last_night_avg, weekly_avg, status, last_updated
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                last_night_avg=excluded.last_night_avg,
                weekly_avg=excluded.weekly_avg,
                status=excluded.status,
                last_updated=excluded.last_updated
        '''
        
        cursor.execute(query, (
            data.get('date'),
            data.get('last_night_avg'),
            data.get('weekly_avg'),
            data.get('status'),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()

    def upsert_activity(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            INSERT INTO activities (
                activity_id, activity_name, activity_type, start_time, distance_meters,
                duration_seconds, avg_hr, max_hr, calories, avg_power, max_power,
                elevation_gain_meters, elevation_loss_meters, avg_cadence, max_cadence, steps, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(activity_id) DO UPDATE SET
                activity_name=excluded.activity_name,
                activity_type=excluded.activity_type,
                start_time=excluded.start_time,
                distance_meters=excluded.distance_meters,
                duration_seconds=excluded.duration_seconds,
                avg_hr=excluded.avg_hr,
                max_hr=excluded.max_hr,
                calories=excluded.calories,
                avg_power=excluded.avg_power,
                max_power=excluded.max_power,
                elevation_gain_meters=excluded.elevation_gain_meters,
                elevation_loss_meters=excluded.elevation_loss_meters,
                avg_cadence=excluded.avg_cadence,
                max_cadence=excluded.max_cadence,
                steps=excluded.steps,
                last_updated=excluded.last_updated
        '''
        
        cursor.execute(query, (
            data.get('activity_id'),
            data.get('activity_name'),
            data.get('activity_type'),
            data.get('start_time'),
            data.get('distance_meters'),
            data.get('duration_seconds'),
            data.get('avg_hr'),
            data.get('max_hr'),
            data.get('calories'),
            data.get('avg_power'),
            data.get('max_power'),
            data.get('elevation_gain_meters'),
            data.get('elevation_loss_meters'),
            data.get('avg_cadence'),
            data.get('max_cadence'),
            data.get('steps'),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
