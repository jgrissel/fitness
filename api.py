import os
from fastapi import FastAPI, HTTPException, Query, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd
from datetime import datetime, timedelta
import logging
from db_manager import DBManager
from activity_parser import parse_activity_details

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Garmin Data API")

# Authentication
API_TOKEN_NAME = "token"
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_api_token(
    token: str = Query(None),
    header_auth: str = Security(api_key_header)
):
    expected_token = os.getenv("API_TOKEN")
    if not expected_token:
        # If no token configured on server, allow access (or blocking it? default to allow for back-compat unless strict)
        # Plan said default 401. Let's make it secure by default.
        raise HTTPException(status_code=500, detail="Server misconfigured: API_TOKEN not set")

    # Check query param
    if token == expected_token:
        return token

    # Check header (Bearer <token>)
    if header_auth:
        if header_auth.startswith("Bearer "):
            header_token = header_auth.split(" ")[1]
            if header_token == expected_token:
                return header_token
        # Also support just raw token in header for simplicity if user messes up Bearer
        if header_auth == expected_token:
            return header_auth

    raise HTTPException(status_code=401, detail="Unauthorized")

def get_db_data(query, params=None):
    """Helper to fetch data into a Pandas DataFrame."""
    # Let exceptions bubble up so we can see them in the browser
    db = DBManager()
    
    conn = db.get_connection()
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

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

from fastapi import Response

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

def set_no_cache(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

@app.get("/daily", response_class=HTMLResponse)
def get_daily(response: Response):
    set_no_cache(response)
    try:
        df = get_db_data("SELECT * FROM daily_summary ORDER BY date DESC")
        return df_to_html(df, "Daily Summary")
    except Exception as e:
        return f"<h3>Error loading Daily Summary</h3><p>{e}</p>"

@app.get("/sleep", response_class=HTMLResponse)
def get_sleep(response: Response):
    set_no_cache(response)
    try:
        df = get_db_data("SELECT * FROM sleep_summary ORDER BY date DESC")
        return df_to_html(df, "Sleep Summary")
    except Exception as e:
        return f"<h3>Error loading Sleep Summary</h3><p>{e}</p>"

@app.get("/hrv", response_class=HTMLResponse)
def get_hrv(response: Response):
    set_no_cache(response)
    try:
        df = get_db_data("SELECT * FROM hrv_summary ORDER BY date DESC")
        return df_to_html(df, "HRV Summary")
    except Exception as e:
        return f"<h3>Error loading HRV Summary</h3><p>{e}</p>"

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

@app.get("/export/latest", response_class=JSONResponse)
def export_latest_bundle(auth: str = Depends(get_api_token)):
    """
    Returns a JSON bundle of the latest data for AI consumption.
    Includes: Daily Summary, Sleep, HRV, and last 5 Activities (with details).
    """
    try:
        db = DBManager()
        bundle = {}

        # 1. Summaries (Latest Record)
        # Using helper to get DataFrame, then converting to dict
        daily = get_db_data("SELECT * FROM daily_summary ORDER BY date DESC LIMIT 1")
        # Fix NaN for JSON
        daily = daily.astype(object).where(pd.notnull(daily), None)
        bundle['daily'] = daily.to_dict(orient='records')[0] if not daily.empty else None

        sleep = get_db_data("SELECT * FROM sleep_summary ORDER BY date DESC LIMIT 1")
        sleep = sleep.astype(object).where(pd.notnull(sleep), None)
        bundle['sleep'] = sleep.to_dict(orient='records')[0] if not sleep.empty else None

        hrv = get_db_data("SELECT * FROM hrv_summary ORDER BY date DESC LIMIT 1")
        hrv = hrv.astype(object).where(pd.notnull(hrv), None)
        bundle['hrv'] = hrv.to_dict(orient='records')[0] if not hrv.empty else None

        # 2. Recent Activities (Last 5)
        activities_df = get_db_data("SELECT * FROM activities ORDER BY start_time DESC LIMIT 5")
        activities_df = activities_df.astype(object).where(pd.notnull(activities_df), None)
        activities_list = []
        
        if not activities_df.empty:
            for _, act in activities_df.iterrows():
                act_dict = act.to_dict()
                act_id = int(act['activity_id'])
                
                # Attach details if available
                details_json = db.get_activity_details_json(act_id)
                if details_json:
                    # Simplify details for AI context window if needed, or send raw
                    # For now, let's parse it to a simplified list of samples
                    df_details = parse_activity_details(details_json)
                    if not df_details.empty:
                        # Resample to reduce token usage (e.g., every 10th row)
                        step = max(1, len(df_details) // 50) 
                        df_sampled = df_details.iloc[::step]
                        
                        # Fix NaN in samples
                        df_sampled = df_sampled.astype(object).where(pd.notnull(df_sampled), None)
                        
                        # Convert timestamps to string for JSON serialization
                        json_details = df_sampled.to_dict(orient='records')
                        # Sanitize timestamps
                        for record in json_details:
                            if 'timestamp' in record and isinstance(record['timestamp'], (datetime, pd.Timestamp)):
                                record['timestamp'] = str(record['timestamp'])
                        
                        act_dict['samples'] = json_details
                    else:
                        act_dict['samples'] = []
                else:
                    act_dict['samples'] = None
                
                # Sanitize main activity timestamps
                if 'start_time' in act_dict and isinstance(act_dict['start_time'], (datetime, pd.Timestamp)):
                    act_dict['start_time'] = str(act_dict['start_time'])
                if 'last_updated' in act_dict and isinstance(act_dict['last_updated'], (datetime, pd.Timestamp)):
                    act_dict['last_updated'] = str(act_dict['last_updated'])

                activities_list.append(act_dict)

        bundle['activities'] = activities_list
        bundle['generated_at'] = str(datetime.now())
        
        return bundle

    except Exception as e:
        logger.error(f"Error generating bundle: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
