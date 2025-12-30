from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
import pandas as pd
from datetime import datetime, timedelta
import logging
from db_manager import DBManager
from activity_parser import parse_activity_details

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Garmin Data API")

def get_db_data(query, params=None):
    """Helper to fetch data into a Pandas DataFrame."""
    try:
        db = DBManager()
        conn = db.get_connection()
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Database error: {e}")
        return pd.DataFrame()

def df_to_html(df, title="Data Export"):
    """Converts DataFrame to a clean HTML table."""
    if df.empty:
        return f"<h3>{title}</h3><p>No data found.</p>"
    
    html = f"""
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            h2 {{ color: #333; }}
        </style>
    </head>
    <body>
        <h2>{title}</h2>
        <p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Records: {len(df)}</p>
        {df.to_html(index=False)}
    </body>
    </html>
    """
    return html

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <h1>Garmin Data API</h1>
    <ul>
        <li><a href="/daily">/daily</a> - Daily Summary Stats</li>
        <li><a href="/sleep">/sleep</a> - Sleep Data</li>
        <li><a href="/hrv">/hrv</a> - HRV Data</li>
        <li><a href="/activities/export">/activities/export</a> - <b>FULL Export (Last 6 Months)</b></li>
    </ul>
    """

@app.get("/daily", response_class=HTMLResponse)
def get_daily():
    df = get_db_data("SELECT * FROM daily_summary ORDER BY date DESC")
    return df_to_html(df, "Daily Summary")

@app.get("/sleep", response_class=HTMLResponse)
def get_sleep():
    df = get_db_data("SELECT * FROM sleep_summary ORDER BY date DESC")
    return df_to_html(df, "Sleep Summary")

@app.get("/hrv", response_class=HTMLResponse)
def get_hrv():
    df = get_db_data("SELECT * FROM hrv_summary ORDER BY date DESC")
    return df_to_html(df, "HRV Summary")

@app.get("/activities/export", response_class=HTMLResponse)
def export_activities(months: int = Query(6, ge=1, le=24)):
    """
    Exports all activities from the last X months into a single HTML report.
    Includes summary stats AND detailed metrics (resampled to decent resolution).
    """
    import traceback
    try:
        db = DBManager()
        
        # 1. Fetch Activities
        cutoff_date = datetime.now() - timedelta(days=30 * months)
        query = "SELECT * FROM activities WHERE start_time >= %s ORDER BY start_time DESC"
        activities_df = get_db_data(query, (cutoff_date,))
        
        if activities_df.empty:
            return "<h3>Activity Export</h3><p>No activities found in the selected range.</p>"
        
        # Start building the massive HTML string
        html_parts = ["""
        <html>
        <head>
            <title>Activity Export</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                .activity {{ border: 1px solid #ccc; margin-bottom: 30px; padding: 15px; border-radius: 5px; }}
                .header {{ background-color: #eee; padding: 10px; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; font-size: 0.9em; }}
                th, td {{ border: 1px solid #ddd; padding: 4px; text-align: right; }}
                th {{ text-align: center; background-color: #f8f8f8; }}
            </style>
        </head>
        <body>
        <h1>Activity Export (Last {} Months)</h1>
        <p>Generated: {}</p>
        <hr>
        """.format(months, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
        
        # 2. Iterate and Append Details
        for _, act in activities_df.iterrows():
            act_id = int(act['activity_id'])
            
            # Header Info
            header_html = f"""
            <div class="activity">
                <div class="header">
                    {act['start_time']} - {act['activity_name']} ({act['activity_type']})<br>
                    Dist: {act['distance_meters']:.1f}m | Dur: {act['duration_seconds']}s | HR: {act['avg_hr']} | Cal: {act['calories']}
                </div>
            """
            html_parts.append(header_html)
            
            # Fetch Details
            details_json = db.get_activity_details_json(act_id)
            if details_json:
                df_details = parse_activity_details(details_json)
                if not df_details.empty:
                    # OPTIMIZATION: Resample to reduce size if row count is huge
                    # For ChatGPT, 1-second resolution for a 2-hour run is ~7200 rows. That's a lot of tokens.
                    # Let's resample to 1-minute intervals (approx) or take every 60th row if no timestamp index
                    
                    if len(df_details) > 300:
                        # Keep roughly 100-200 data points per activity for readability/context window
                        # This gives enough fidelity for "digging in" without overwhelming
                        step = max(1, len(df_details) // 100)
                        df_details = df_details.iloc[::step]
                    
                    # Filter columns to interesting ones
                    cols_to_keep = [c for c in ['timestamp', 'heart_rate', 'power', 'cadence', 'speed', 'elevation'] if c in df_details.columns]
                    if cols_to_keep:
                        html_parts.append("<h4>Sampled Metrics (Every ~1% of duration)</h4>")
                        html_parts.append(df_details[cols_to_keep].to_html(index=False, border=0))
                    else:
                        html_parts.append("<p><i>No detailed metrics available (columns missing).</i></p>")
                else:
                    html_parts.append("<p><i>Detailed metrics parsed empty.</i></p>")
            else:
                html_parts.append("<p><i>No detailed metrics in database.</i></p>")
                
            html_parts.append("</div>") # Close activity div
            
        html_parts.append("</body></html>")
        return "".join(html_parts)
    except Exception:
        return f"<h3>Internal Server Error</h3><pre>{traceback.format_exc()}</pre>"
