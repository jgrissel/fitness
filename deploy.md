# Deployment Guide (Google Cloud)

## Prerequisites
1.  Google Cloud Project.
2.  `gcloud` CLI installed and authenticated.
3.  Garmin credentials.

## 1. Setup Storage (GCS)
Create a bucket to store your database.
```bash
gcloud storage buckets create gs://YOUR_BUCKET_NAME --location=us-central1
```

## 2. Build Container
Submit the build to Cloud Build.
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/garmin-logger
```

## 3. Deploy Logger (Cloud Run Job)
This job runs the extraction script. We mount the bucket to `/mnt/data`.

```bash
gcloud run jobs create garmin-logger-job \
  --image gcr.io/YOUR_PROJECT_ID/garmin-logger \
  --region us-central1 \
  --command python \
  --args main.py,--once \
  --set-env-vars GARMIN_EMAIL=your_email,GARMIN_PASSWORD=your_password,DB_PATH=/mnt/data/garmin_data.db \
  --add-volume name=garmin-data,type=cloud-storage,bucket=YOUR_BUCKET_NAME \
  --add-volume-mount volume=garmin-data,mount-path=/mnt/data \
  --execution-environment=gen2
```

## 4. Schedule Logger
Run every hour.
```bash
gcloud scheduler jobs create http garmin-logger-schedule \
  --location us-central1 \
  --schedule "0 * * * *" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT_ID/jobs/garmin-logger-job:run" \
  --http-method POST \
  --oauth-service-account-email YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com
```
*(Note: You might need to adjust the URI or use the Console UI to trigger the job easily).*

## 5. Deploy Dashboard (Cloud Run Service)
This service hosts the web viewer.

```bash
gcloud run deploy garmin-dashboard \
  --image gcr.io/YOUR_PROJECT_ID/garmin-logger \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars DB_PATH=/mnt/data/garmin_data.db \
  --add-volume name=garmin-data,type=cloud-storage,bucket=YOUR_BUCKET_NAME \
  --add-volume-mount volume=garmin-data,mount-path=/mnt/data \
  --execution-environment=gen2
```

## 6. Backfill on Cloud
To run a backfill, you can execute the job manually with overrides, or just run it locally pointing to the downloaded DB, then re-upload.
Or, create a one-off job:
```bash
gcloud run jobs create garmin-backfill \
  --image gcr.io/YOUR_PROJECT_ID/garmin-logger \
  --region us-central1 \
  --command python \
  --args backfill.py,--start,2024-01-01,--end,2024-12-31 \
  --set-env-vars GARMIN_EMAIL=...,GARMIN_PASSWORD=...,DB_PATH=/mnt/data/garmin_data.db \
  --add-volume name=garmin-data,type=cloud-storage,bucket=YOUR_BUCKET_NAME \
  --add-volume-mount volume=garmin-data,mount-path=/mnt/data \
  --execution-environment=gen2
```
