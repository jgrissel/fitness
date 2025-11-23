import os
import logging
from datetime import date, datetime, timedelta
from garminconnect import Garmin
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GarminClient:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv("GARMIN_EMAIL")
        self.password = os.getenv("GARMIN_PASSWORD")
        self.client = None

    def login(self):
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            logger.info("Garmin Connect login successful.")
            return True
        except Exception as e:
            logger.error(f"Failed to login to Garmin Connect: {e}")
            return False

    def get_daily_summary(self, day: date):
        try:
            data = self.client.get_user_summary(day.isoformat())
            
            # Parse relevant fields
            parsed = {
                'date': data.get('calendarDate'),
                'total_steps': data.get('totalSteps'),
                'total_distance_meters': data.get('totalDistanceMeters'),
                'active_kcal': data.get('activeKilocalories'),
                'bmr_kcal': data.get('bmrKilocalories'),
                'total_kcal': data.get('totalKilocalories'),
                'resting_hr': data.get('restingHeartRate'),
                'min_hr': data.get('minHeartRate'),
                'max_hr': data.get('maxHeartRate'),
                'avg_stress': data.get('averageStressLevel'),
                'max_stress': data.get('maxStressLevel'),
                'body_battery_current': data.get('bodyBatteryMostRecentValue'),
                'body_battery_high': data.get('bodyBatteryHighestValue'),
                'body_battery_low': data.get('bodyBatteryLowestValue'),
            }
            return parsed
        except Exception as e:
            logger.error(f"Error fetching daily summary for {day}: {e}")
            return None

    def get_sleep_data(self, day: date):
        try:
            data = self.client.get_sleep_data(day.isoformat())
            dto = data.get('dailySleepDTO', {})
            
            parsed = {
                'date': dto.get('calendarDate'),
                'total_sleep_seconds': dto.get('sleepTimeSeconds'),
                'deep_sleep_seconds': dto.get('deepSleepSeconds'),
                'light_sleep_seconds': dto.get('lightSleepSeconds'),
                'rem_sleep_seconds': dto.get('remSleepSeconds'),
                'awake_sleep_seconds': dto.get('awakeSleepSeconds'),
                'sleep_score': dto.get('sleepScores', {}).get('overall', {}).get('value'),
                'sleep_quality': dto.get('sleepScores', {}).get('overall', {}).get('qualifierKey'),
            }
            return parsed
        except Exception as e:
            logger.error(f"Error fetching sleep data for {day}: {e}")
            return None

    def get_hrv_data(self, day: date):
        try:
            data = self.client.get_hrv_data(day.isoformat())
            summary = data.get('hrvSummary', {})
            
            parsed = {
                'date': summary.get('calendarDate'),
                'last_night_avg': summary.get('lastNightAvg'),
                'weekly_avg': summary.get('weeklyAvg'),
                'status': summary.get('status'),
            }
            return parsed
        except Exception as e:
            logger.error(f"Error fetching HRV data for {day}: {e}")
            return None

    def get_activities(self, start_index=0, limit=10):
        try:
            activities = self.client.get_activities(start_index, limit)
            parsed_activities = []
            
            for act in activities:
                parsed = {
                    'activity_id': act.get('activityId'),
                    'activity_name': act.get('activityName'),
                    'activity_type': act.get('activityType', {}).get('typeKey'),
                    'start_time': act.get('startTimeLocal'),
                    'distance_meters': act.get('distance'),
                    'duration_seconds': act.get('duration'),
                    'avg_hr': act.get('averageHR'),
                    'max_hr': act.get('maxHR'),
                    'calories': act.get('calories'),
                    'avg_power': act.get('avgPower'),
                    'max_power': act.get('maxPower'),
                    'elevation_gain_meters': act.get('elevationGain'),
                    'elevation_loss_meters': act.get('elevationLoss'),
                    'avg_cadence': act.get('averageBikingCadenceInRevPerMinute') or act.get('averageRunningCadenceInStepsPerMinute'),
                    'max_cadence': act.get('maxBikingCadenceInRevPerMinute') or act.get('maxRunningCadenceInStepsPerMinute'),
                    'steps': act.get('steps'),
                }
                parsed_activities.append(parsed)
                
            return parsed_activities
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []
