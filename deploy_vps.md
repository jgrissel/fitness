# Deployment Guide (Linux VPS)

This guide explains how to deploy the Garmin Health Data Logger and Dashboard to a Linux server (e.g., DigitalOcean, Linode, AWS EC2) using Docker Compose.

## Prerequisites

1.  A Linux server (Ubuntu recommended).
2.  **Docker** and **Docker Compose** installed on the server.
    *   *Quick Install (Ubuntu):* `sudo apt update && sudo apt install docker.io docker-compose -y`

## Deployment Steps

1.  **Clone the Repository**
    SSH into your server and clone your repo:
    ```bash
    git clone https://github.com/jgrissel/fitness.git
    cd fitness
    ```

2.  **Configure Credentials**
    Create a `.env` file with your Garmin login:
    ```bash
    nano .env
    ```
    Paste the following (replace with your details):
    ```env
    GARMIN_EMAIL=your_email@example.com
    GARMIN_PASSWORD=your_password
    ```
    *Press `Ctrl+X`, then `Y`, then `Enter` to save.*

3.  **Start the Services**
    Run Docker Compose to build and start the containers in the background:
    ```bash
    sudo docker-compose up -d --build
    ```

4.  **Access the Dashboard**
    Open your browser and go to:
    `http://YOUR_SERVER_IP:8501`

## Management

*   **View Logs**:
    ```bash
    sudo docker-compose logs -f
    ```
*   **Stop Services**:
    ```bash
    sudo docker-compose down
    ```
*   **Update Code**:
    ```bash
    git pull
    sudo docker-compose up -d --build
    ```

## Backfilling Data
To run a backfill on the server, you can execute a one-off command inside the logger container:

```bash
sudo docker-compose exec logger python backfill.py --start 2024-01-01 --end 2024-12-31
```
