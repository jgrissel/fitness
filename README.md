# Garmin Health Data Logger & Dashboard

A comprehensive tool to extract, store, and visualize your Garmin health data (Steps, Sleep, HRV, Activities).

## Features

-   **Automated Logging**: Fetches data from Garmin Connect API every hour.
-   **Local Database**: Stores everything in a lightweight SQLite database (`garmin_data.db`).
-   **Interactive Dashboard**: A beautiful web interface (Streamlit) to explore your metrics.
-   **Historical Backfill**: Fetch past data for any date range.
-   **Cloud Ready**: Includes Dockerfile and deployment scripts for Google Cloud.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/jgrissel/fitness.git
    cd fitness
    ```

2.  **Install Dependencies**:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configure Credentials**:
    Create a `.env` file in the root directory:
    ```env
    GARMIN_EMAIL=your_email@example.com
    GARMIN_PASSWORD=your_password
    ```

## Usage

### 1. Start the Logger
To start the hourly data extraction scheduler:
Double-click `start_logger.bat` or run:
```bash
python main.py
```

### 2. View the Dashboard
To open the web visualization:
Double-click `run_dashboard.bat` or run:
```bash
streamlit run dashboard.py
```

### 3. Backfill Old Data
To fetch historical data (e.g., last year):
Double-click `run_backfill.bat` or run:
```bash
python backfill.py --start 2024-01-01 --end 2024-12-31
```

## Database Schema

The SQLite database contains the following tables:
-   `daily_summary`: Steps, Resting HR, Body Battery, Stress.
-   `sleep_summary`: Sleep duration, stages (Deep/Light/REM), Sleep Score.
-   `hrv_summary`: Nightly HRV average and status.
-   `activities`: Detailed stats for runs, rides, hikes, etc.

## Deployment

### Google Cloud (Serverless)
Deploy to Cloud Run (scales to zero). See [deploy.md](deploy.md).

### Linux VPS (Docker Compose)
Deploy to any Linux server (DigitalOcean, Linode, etc.). See [deploy_vps.md](deploy_vps.md).
