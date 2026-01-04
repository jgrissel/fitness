import os
import io
import zipfile
import hashlib
from fastapi import FastAPI, HTTPException, Query, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
import pandas as pd
import numpy as np
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
        raise HTTPException(status_code=500, detail="Server misconfigured: API_TOKEN not set")

    if token == expected_token:
        return token

    if header_auth:
        if header_auth.startswith("Bearer "):
            header_token = header_auth.split(" ")[1]
            if header_token == expected_token:
                return header_token
        if header_auth == expected_token:
            return header_auth

    raise HTTPException(status_code=401, detail="Unauthorized")

def get_db_data(query, params=None):
    """Helper to fetch data into a Pandas DataFrame."""
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

def set_no_cache(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <h1>Garmin Data API</h1>
    <ul>
        <li><a href="/daily">/daily</a> - Daily Summary Stats</li>
        <li><a href="/sleep">/sleep</a> - Sleep Data</li>
        <li><a href="/hrv">/hrv</a> - HRV Data</li>
        <li><a href="/export/index">/export/index</a> - <b>AI Data Index</b></li>
    </ul>
    """

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

# ------------------------------------------------------------------------------
# NEW: File-Based Export Endpoints
# ------------------------------------------------------------------------------

DOMAIN = "https://fitness.grissel.dev" # Hardcoded as per config

@app.get("/export/index", response_class=JSONResponse)
def export_index(response: Response, auth: str = Depends(get_api_token)):
    """
    Returns a lightweight JSON index pointing to downloadable CSV/ZIP assets.
    """
    set_no_cache(response)
    try:
        # Get Time Range
        db = DBManager()
        # Efficiently get min/max date from activities (or daily)
        range_df = get_db_data("SELECT MIN(start_time), MAX(start_time) FROM activities")
        min_date = range_df.iloc[0, 0] if not range_df.empty and range_df.iloc[0, 0] else datetime.now()
        max_date = range_df.iloc[0, 1] if not range_df.empty and range_df.iloc[0, 1] else datetime.now()

        # Construct Index
        index_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "schema_version": "1.0.0",
            "source_range": {
                "start": str(min_date),
                "end": str(max_date)
            },
            "athlete": {
                "name": "James",
                "ftp_anchor": 203 # Placeholder/Configurable
            },
            "files": {
                "daily_metrics_csv": f"{DOMAIN}/exports/daily_metrics.csv?token={auth}",
                "activities_index_csv": f"{DOMAIN}/exports/activities_index.csv?token={auth}",
                "activities_detail_zip": f"{DOMAIN}/exports/activities_detail.zip?token={auth}"
            }
            # Note: Hash not included yet to keep index response fast (requires reading all data)
        }
        return index_data
    except Exception as e:
        logger.error(f"Error generating index: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/exports/daily_metrics.csv")
def export_daily_csv(response: Response, auth: str = Depends(get_api_token)):
    set_no_cache(response)
    try:
        # Join Daily + Sleep + HRV for a consolidated view
        # Using FULL OUTER JOINs or just Left Joins if Daily is the anchor
        query = """
            SELECT 
                d.date,
                d.total_steps,
                d.total_distance_meters,
                d.active_kcal,
                d.resting_hr,
                d.min_hr,
                d.max_hr,
                d.avg_stress,
                d.body_battery_low, 
                d.body_battery_high,
                s.total_sleep_seconds,
                s.sleep_score,
                s.sleep_quality,
                h.last_night_avg as hrv_last_night_avg,
                h.status as hrv_status
            FROM daily_summary d
            LEFT JOIN sleep_summary s ON d.date = s.date
            LEFT JOIN hrv_summary h ON d.date = h.date
            ORDER BY d.date DESC
        """
        df = get_db_data(query)
        
        # Ensure 'sleep_hours' exists if preferred
        if 'total_sleep_seconds' in df.columns:
             df['sleep_hours'] = df['total_sleep_seconds'] / 3600.0
        
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=daily_metrics.csv"
        return response
    except Exception as e:
        logger.error(f"Error exporting daily csv: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/exports/activities_index.csv")
def export_activities_csv(response: Response, auth: str = Depends(get_api_token)):
    set_no_cache(response)
    try:
        # Specific columns requested
        query = """
            SELECT 
                activity_id,
                start_time,
                activity_type as sport,
                duration_seconds,
                distance_meters,
                avg_power,
                max_power,
                avg_hr,
                max_hr,
                elevation_gain_meters,
                calories
            FROM activities
            ORDER BY start_time DESC
        """
        df = get_db_data(query)
        
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=activities_index.csv"
        return response
    except Exception as e:
        logger.error(f"Error exporting activities csv: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/exports/activities_detail.zip")
def export_activities_zip(response: Response, auth: str = Depends(get_api_token)):
    set_no_cache(response)
    try:
        db = DBManager()
        # Fetch last 90 days of activity IDs
        # To avoid massive creation, stick to limits for now or stream
        # Creating a ZIP in memory
        
        # 1. Get List of Activities
        ids = db.get_recent_activity_ids(days=90) # Default 60 in db_manager, we override to 90
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for act_id in ids:
                details = db.get_activity_details_json(act_id)
                if details:
                    # Parse to DataFrame just to normalize/sample if needed, 
                    # OR just dump the raw JSON which is preserved in DB. 
                    # Raw JSON is better for "details" export usually.
                    # But user wanted 'stable columns'. 
                    # Let's dump the RAW JSON for maximum fidelity, as parsing CSVs for every activity in a zip is weird.
                    # Actually, usually 'details.zip' implies either JSONs or CSVs. JSON is standard.
                    import json
                    
                    # We can use the 'parse_activity_details' if we want to enforce standard columns 
                    # and save as CSV inside the ZIP. 
                    # Let's save as JSON for flexibility, or CSV if strict schema needed.
                    # User said "activities_detail.zip", didn't specify format inside, 
                    # but context of "Linked Index" usually implies getting the raw time series.
                    # Let's stick to JSON for the details files.
                    
                    # Fix NaNs before dumping
                    # If details is a list of dicts (which it usually is from Garmin)
                    
                    fname = f"activity_{act_id}.json"
                    zip_file.writestr(fname, json.dumps(details, default=str)) # default=str handles dates
        
        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]), 
            media_type="application/zip", 
            headers={"Content-Disposition": "attachment; filename=activities_detail.zip"}
        )

    except Exception as e:
        logger.error(f"Error exporting zip: {e}")
        raise HTTPException(status_code=500, detail=str(e))

