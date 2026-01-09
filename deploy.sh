#!/bin/bash

echo "🚀 Preparing for Google Cloud Run Deployment..."

# 1. Auto-detect Project ID
echo "🔍 Detecting Google Cloud Project..."
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    # Fallback to user provided ID
    PROJECT_ID="caparox-bot"
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Could not auto-detect Project ID."
    read -p "👉 Please enter your Google Cloud Project ID manually: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: No Project ID provided. Exiting."
    exit 1
fi

echo "✅ Using Project ID: $PROJECT_ID"

# Set Project explicitly
gcloud config set project $PROJECT_ID

REGION="us-central1"
SERVICE_NAME="caparox-bot"
BUCKET_NAME="${PROJECT_ID}-data"

# 2. Enable APIs
echo "🛠 Enabling necessary APIs (Cloud Build, Cloud Run)..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com --project $PROJECT_ID

# 3. Build the Docker image
echo "📦 Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME --project $PROJECT_ID

# 4. Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."

# Env Vars string
ENV_VARS="PYTHONUNBUFFERED=1"
ENV_VARS+=",GCS_BUCKET_NAME=${BUCKET_NAME}"
ENV_VARS+=",FLUTTERWAVE_PUBLIC_KEY=FLWPUBK-aded1251ab1fccfd69b058608f38f7a8-X"
ENV_VARS+=",FLUTTERWAVE_SECRET_KEY=FLWSECK-2d9e29e2c7e85214e55fa642cff59b99-19b9abc3310vt-X"
ENV_VARS+=",FLUTTERWAVE_ENCRYPTION_KEY=2d9e29e2c7e8eaa49db18d1b"

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "$ENV_VARS" \
  --memory 2Gi \
  --cpu 2

echo "✅ Deployment complete!"
