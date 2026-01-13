#!/bin/bash
# Deploy to Google Cloud Run

PROJECT_ID="caparox-bot"
SERVICE_NAME="caparox-bot"
REGION="us-central1"

echo "Deploying $SERVICE_NAME to Google Cloud Run..."

# 1. Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 2. Deploy
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --update-env-vars "FLASK_ENV=production"

echo "Deployment Complete!"
