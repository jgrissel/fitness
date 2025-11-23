import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page Config
st.set_page_config(page_title="Garmin Health Dashboard", page_icon="🏃", layout="wide")

# Database Connection
@st.cache_data
def load_data():
    conn = sqlite3.connect("garmin_data.db")
    
    daily = pd.read_sql_query("SELECT * FROM daily_summary ORDER BY date DESC", conn)
    sleep = pd.read_sql_query("SELECT * FROM sleep_summary ORDER BY date DESC", conn)
    hrv = pd.read_sql_query("SELECT * FROM hrv_summary ORDER BY date DESC", conn)
    activities = pd.read_sql_query("SELECT * FROM activities ORDER BY start_time DESC", conn)
    
    conn.close()
    return daily, sleep, hrv, activities

try:
    daily_df, sleep_df, hrv_df, activities_df = load_data()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Sidebar
st.sidebar.title("Garmin Dashboard")
st.sidebar.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Backfill Data")
with st.sidebar.form("backfill_form"):
    start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
    end_date = st.date_input("End Date", value=datetime.now().date())
    submit_backfill = st.form_submit_button("Start Backfill")

if submit_backfill:
    if start_date > end_date:
        st.sidebar.error("Start date must be before end date.")
    else:
        st.sidebar.info("Starting backfill... This may take a while.")
        try:
            # Import here to avoid circular imports if any, and keep main load fast
            from backfill import backfill_data
            with st.spinner(f"Backfilling from {start_date} to {end_date}..."):
                backfill_data(start_date, end_date)
            st.sidebar.success("Backfill completed!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"An error occurred: {e}")

# Main Dashboard
st.title("🏃 Garmin Health Dashboard")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Sleep", "HRV", "Activities"])

with tab1:
    st.header("Daily Overview")
    
    if not daily_df.empty:
        latest = daily_df.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Steps", f"{latest['total_steps']:,}", delta=f"{latest['total_steps'] - daily_df.iloc[1]['total_steps']:,}" if len(daily_df) > 1 else None)
        col2.metric("Resting HR", f"{latest['resting_hr']} bpm")
        col3.metric("Body Battery", f"{latest['body_battery_current']}", f"{latest['body_battery_high']}/{latest['body_battery_low']}")
        col4.metric("Stress", f"{latest['avg_stress']}")

        st.subheader("Trends (Last 30 Days)")
        
        # Steps Chart
        fig_steps = px.bar(daily_df.head(30), x='date', y='total_steps', title="Daily Steps")
        st.plotly_chart(fig_steps, use_container_width=True)
        
        # Body Battery & Stress
        fig_bb = go.Figure()
        fig_bb.add_trace(go.Scatter(x=daily_df.head(30)['date'], y=daily_df.head(30)['body_battery_high'], name='Max Body Battery', line=dict(color='blue')))
        fig_bb.add_trace(go.Scatter(x=daily_df.head(30)['date'], y=daily_df.head(30)['body_battery_low'], name='Min Body Battery', line=dict(color='lightblue')))
        fig_bb.add_trace(go.Scatter(x=daily_df.head(30)['date'], y=daily_df.head(30)['avg_stress'], name='Avg Stress', line=dict(color='orange'), yaxis='y2'))
        
        fig_bb.update_layout(
            title="Body Battery & Stress",
            yaxis=dict(title="Body Battery"),
            yaxis2=dict(title="Stress", overlaying='y', side='right')
        )
        st.plotly_chart(fig_bb, use_container_width=True)
    else:
        st.warning("No daily data found.")

with tab2:
    st.header("Sleep Analysis")
    
    if not sleep_df.empty:
        col1, col2 = st.columns(2)
        latest_sleep = sleep_df.iloc[0]
        
        # Convert seconds to hours for display
        total_hours = latest_sleep['total_sleep_seconds'] / 3600
        col1.metric("Last Night's Sleep", f"{total_hours:.1f} hrs")
        col2.metric("Sleep Score", f"{latest_sleep['sleep_score']}", f"{latest_sleep['sleep_quality']}")
        
        # Sleep Duration Chart
        sleep_df['hours'] = sleep_df['total_sleep_seconds'] / 3600
        fig_sleep = px.bar(sleep_df.head(30), x='date', y='hours', title="Sleep Duration (Hours)", color='sleep_score')
        st.plotly_chart(fig_sleep, use_container_width=True)
        
        # Sleep Stages
        st.subheader("Sleep Stages (Last 7 Days)")
        stages_df = sleep_df.head(7).copy()
        stages_df['Deep'] = stages_df['deep_sleep_seconds'] / 3600
        stages_df['Light'] = stages_df['light_sleep_seconds'] / 3600
        stages_df['REM'] = stages_df['rem_sleep_seconds'] / 3600
        stages_df['Awake'] = stages_df['awake_sleep_seconds'] / 3600
        
        fig_stages = px.bar(stages_df, x='date', y=['Deep', 'Light', 'REM', 'Awake'], title="Sleep Stages Breakdown")
        st.plotly_chart(fig_stages, use_container_width=True)
    else:
        st.warning("No sleep data found.")

with tab3:
    st.header("HRV Status")
    
    if not hrv_df.empty:
        fig_hrv = px.line(hrv_df.head(60), x='date', y='last_night_avg', title="Nightly HRV Average", markers=True)
        # Add weekly avg if available
        fig_hrv.add_trace(go.Scatter(x=hrv_df.head(60)['date'], y=hrv_df.head(60)['weekly_avg'], name='7-Day Avg', line=dict(dash='dash')))
        st.plotly_chart(fig_hrv, use_container_width=True)
    else:
        st.warning("No HRV data found.")

with tab4:
    st.header("Activities")
    
    if not activities_df.empty:
        # Filters
        activity_types = activities_df['activity_type'].unique()
        selected_type = st.multiselect("Filter by Type", activity_types, default=activity_types)
        
        filtered_df = activities_df[activities_df['activity_type'].isin(selected_type)]
        
        st.dataframe(filtered_df[['start_time', 'activity_name', 'activity_type', 'distance_meters', 'duration_seconds', 'avg_hr', 'calories']])
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            fig_act_dist = px.scatter(filtered_df, x='start_time', y='distance_meters', color='activity_type', title="Distance over Time")
            st.plotly_chart(fig_act_dist, use_container_width=True)
            
        with col2:
            fig_act_hr = px.box(filtered_df, x='activity_type', y='avg_hr', title="Avg HR Distribution by Activity")
            st.plotly_chart(fig_act_hr, use_container_width=True)
    else:
        st.warning("No activities found.")
