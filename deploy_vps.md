# Deploying to a Linux VPS (DigitalOcean, Linode, AWS, etc.)

Since you already have other sites running on your VPS, we will run this project in Docker containers alongside them, but use **Nginx** (which is likely already serving your other sites) to route traffic to them.

## 1. Automated Hourly Updates
**Good news:** You do NOT need to set up a cron job on your server.
The `garmin_logger` container has a built-in scheduler (using Python `schedule` library) that runs **every hour** to check for new data. As long as the container is running (`restart: always` is already set), your data will stay fresh automatically.

## 2. Co-existing with Existing Sites (Reverse Proxy)
To access your dashboard comfortably without using ugly port numbers (like `:8501`), and to avoid conflicts, use Nginx as a "Reverse Proxy".

### Step 2.1: Docker Setup
1.  Copy your project to the VPS (e.g., via `git clone`).
2.  Run the containers:
    ```bash
    docker-compose up -d --build
    ```
    *This starts the Dashboard on `localhost:8501` and API on `localhost:8000`. These are internal to the server (if firewall blocks them) or accessible via IP.*

### Step 2.2: Nginx Configuration
Assuming you use Nginx, create a new configuration file for this project.

1.  **Create a new config file:**
    ```bash
    sudo nano /etc/nginx/sites-available/garmin_logger
    ```

2.  **Paste the following (Update `server_name`!):**
    ```nginx
    server {
        listen 80;
        server_name dashboard.yourdomain.com;  # <--- CHANGE THIS

        location / {
            proxy_pass http://localhost:8501;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }
    }

    server {
        listen 80;
        server_name api.yourdomain.com;  # <--- CHANGE THIS

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    ```

3.  **Enable the site:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/garmin_logger /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx
    ```

4.  **SSL (HTTPS) - Highly Recommended:**
    Run Certbot for your new subdomains:
    ```bash
    sudo certbot --nginx -d dashboard.yourdomain.com -d api.yourdomain.com
    ```

Now you can visit `https://dashboard.yourdomain.com` for the UI and `https://api.yourdomain.com/activities/export` for your ChatGPT data!

## 3. Troubleshooting
-   **Database Access**: The database is exposed on port `5432`. If you have *another* PostgreSQL running on the host, this **WILL CONFLICT**.
    -   *Fix*: Change the mapped port in `docker-compose.yml`. Change `"5432:5432"` to `"5433:5432"`.
-   **Logs**: Check functionality with `docker-compose logs -f logger`.
