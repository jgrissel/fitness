# Garmin Health Data Logger & Dashboard

A comprehensive tool to extract, store, and visualize your Garmin health data (Steps, Sleep, HRV, Activities).

## Features

-   **Automated Logging**: Fetches data from Garmin Connect API every hour.
-   **Local Database**: Stores everything in a lightweight SQLite database (`garmin_data.db`).
-   **Interactive Dashboard**: A beautiful web interface (Streamlit) to explore your metrics.
-   **Historical Backfill**: Fetch past data for any date range.
-   **Cloud Ready**: Includes Dockerfile and deployment scripts for Google Cloud.

## Setup

### Recommended: Docker Compose
The easiest way to run the full stack (Logger + Database + Dashboard) is with Docker.
```bash
docker-compose up -d --build
```

### Manual Setup (No Docker)
If you prefer to run this locally without Docker, follow these steps:

1.  **Install PostgreSQL**:
    - Download and install [PostgreSQL](https://www.postgresql.org/download/).
    - Create a database (e.g., `garmin`) and a user/password.

2.  **Clone the repository**:
    ```bash
    git clone https://github.com/jgrissel/fitness.git
    cd fitness
    ```

3.  **Install Dependencies**:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```ini
    GARMIN_EMAIL=your_email@example.com
    GARMIN_PASSWORD=your_password
    
    # PostgreSQL Configuration
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=garmin
    DB_USER=postgres
    DB_PASSWORD=your_db_password
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
To fetch historical data (including full activity details):
Double-click `run_backfill.bat` or run:
```bash
python backfill.py --start 2024-01-01 --end 2024-12-31
```

## Database Schema
The system uses **PostgreSQL**.
-   `activities`: Core activity stats.
-   `activity_details`: **[NEW]** Full second-by-second activity data (Heart Rate, GPS, etc.) stored as JSONB.
-   `daily_summary`, `sleep_summary`, `hrv_summary`: Health metrics.

## Deployment

### Google Cloud (Serverless)
Deploy to Cloud Run (scales to zero). See [deploy.md](deploy.md).

### Linux VPS (Docker Compose)
Deploy to any Linux server (DigitalOcean, Linode, etc.). See [deploy_vps.md](deploy_vps.md).
