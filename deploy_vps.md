# Deploying to a Linux VPS (DigitalOcean, Linode, AWS, etc.)

Since you already have other sites running on your VPS, we will run this project in Docker containers alongside them, but use **Nginx** (which is likely already serving your other sites) to route traffic to them.

## 1. Automated Hourly Updates
**Good news:** You do NOT need to set up a cron job on your server.
The `garmin_logger` container has a built-in scheduler (using Python `schedule` library) that runs **every hour** to check for new data. As long as the container is running (`restart: always` is already set), your data will stay fresh automatically.

## 2. Co-existing with Existing Sites (Reverse Proxy)
To access your dashboard comfortably without using ugly port numbers (like `:8501`), and to avoid conflicts, use Nginx as a "Reverse Proxy".

### Step 2.1: Docker Setup
1.  **Prepare the directory**:
    ```bash
    mkdir -p /home/deploy/containers
    cd /home/deploy/containers
    git clone https://github.com/jgrissel/fitness.git
    cd fitness
    ```
    *(This places the project in `/home/deploy/containers/fitness`)*

2.  **Configure Credentials**:
    Create a `.env` file with your details:
    ```bash
    nano .env
    ```
    Paste the following:
    ```ini
    GARMIN_EMAIL=your_email@example.com
    GARMIN_PASSWORD=your_password
    # Database (Internal Docker DNS)
    DB_HOST=db
    DB_NAME=garmin
    DB_USER=postgres
    DB_PASSWORD=postgres
    ```

3.  **Run the containers**:
    ```bash
      
    ```

### Step 2.2: Nginx Configuration
Assuming you use Nginx, create a new configuration file for this project.

1.  **Create a new config file:**
    ```bash
    sudo nano /etc/nginx/sites-available/garmin_logger
    ```

2.  **Paste the Configuration:**

    **Option A: You have a Domain (e.g., garmin.mysite.com)**
    *Use this if you want `dashboard.yourdomain.com`*
    ```nginx
    server {
        listen 80;
        server_name dashboard.yourdomain.com; # <--- CHANGE THIS

        location / {
            proxy_pass http://localhost:8501;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
    # (Repeat for API on expected domain if needed)
    ```

    **Option B: No Domain (IP Address Only)**
    *Use this to access via `http://YOUR_VPS_IP:8080` (Dashboard) and `:8081` (API).*
    ```nginx
    # Dashboard on Port 8080
    server {
        listen 8080;
        server_name _; # Catch-all

        location / {
            proxy_pass http://localhost:8501;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

    # API on Port 8081
    server {
        listen 8081;
        server_name _;

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
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
-   **Error: `KeyError: 'ContainerConfig'`**: This happens with older `docker-compose` versions (like 1.29.x).
    -   *Fix 1 (Quick)*: remove containers first: `docker-compose down --rmi local` then try again.
    -   *Fix 2 (Better)*: Install the newer Docker Compose plugin:
        ```bash
        sudo apt-get update
        sudo apt-get install docker-compose-plugin
        docker compose up -d --build  # Note: space instead of hyphen
        ```
-   **Error: `401 Unauthorized` (Login Failed)**:
    Garmin blocks logins from Data Center IPs (like your VPS).
    **Fix:** You must log in *locally* and upload the session tokens.
    1.  **Locally**: Run `python generate_tokens.py` (install dependencies first: `pip install garminconnect python-dotenv`).
    2.  This creates a folder named `garmin_tokens`.
    3.  **Transfer**: Upload this folder to your VPS data volume location.
        *   Since we used a named volume `garmin_data`, it's tricky to access directly.
        *   **Easier Fix**: Change `docker-compose.yml` to use a bind mount (folder) instead of a volume, OR verify where the volume is.
        *   **Recommended**: Just copy the tokens to the container directly:
            ```bash
            # 1. Run the container (it will fail login, that's fine)
            # 2. Copy the 'garmin_tokens' folder from your local machine to the VPS
            scp -r garmin_tokens root@your_vps_ip:/home/deploy/containers/fitness/
            
            # 3. Copy from VPS filesystem INTO the running container's volume
            # First, find where docker volume is, often /var/lib/docker/volumes/...
            # EASIER: Send it into the running container
            docker cp garmin_tokens garmin_logger:/data/
            
            # 4. Restart the logger
            docker restart garmin_logger
            ```
