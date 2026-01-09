Write-Host "🚀 Preparing for Google Cloud Run Deployment..." -ForegroundColor Cyan

# Check for gcloud in PATH
if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    $GCLOUD_PATH = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path "$GCLOUD_PATH\gcloud.cmd") {
        Write-Host "⚠️  gcloud not found in PATH. Adding $GCLOUD_PATH temporarily..." -ForegroundColor Yellow
        $env:PATH = "$env:PATH;$GCLOUD_PATH"
    } else {
        Write-Host "❌ gcloud not found. Please restart your terminal if you just installed it." -ForegroundColor Red
        exit 1
    }
}

# Check Auth
$AUTH_LIST = gcloud auth list --format="value(account)" 2>$null
if (-not $AUTH_LIST) {
    Write-Host "⚠️  You are not authenticated with Google Cloud." -ForegroundColor Yellow
    Write-Host "👉 Running 'gcloud auth login'..." -ForegroundColor Cyan
    gcloud auth login
}

# 1. Auto-detect Project ID
Write-Host "🔍 Detecting Google Cloud Project..." -ForegroundColor Yellow
$PROJECT_ID = gcloud config get-value project 2>$null

# Hardcode fallback if unset or empty
if ([string]::IsNullOrWhiteSpace($PROJECT_ID) -or $PROJECT_ID -eq '(unset)') {
    $PROJECT_ID = "caparox-bot"
}



if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
    Write-Host "Could not auto-detect Project ID." -ForegroundColor Red
    $PROJECT_ID = Read-Host "Please enter your Google Cloud Project ID manually"
}

if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
    Write-Host "❌ ERROR: No Project ID provided. Exiting." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Using Project ID: $PROJECT_ID" -ForegroundColor Green

# Set Project explicitly to avoid future errors
gcloud config set project $PROJECT_ID

$REGION = "us-central1"
$SERVICE_NAME = "caparox-bot"
$BUCKET_NAME = "${PROJECT_ID}-data"

# 2. Enable APIs
Write-Host "🛠 Enabling necessary APIs (Cloud Build, Cloud Run)..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com run.googleapis.com --project $PROJECT_ID

# 3. Build
Write-Host "📦 Building Docker image..." -ForegroundColor Yellow
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME --project $PROJECT_ID

# 4. Deploy
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Yellow
# Hardcoded Keys for Cloud Run Environment
$ENV_VARS = "PYTHONUNBUFFERED=1," + `
            "GOOGLE_CLOUD_PROJECT=$PROJECT_ID," + `
            "GCS_BUCKET_NAME=$BUCKET_NAME," + `
            "FLUTTERWAVE_PUBLIC_KEY=FLWPUBK-aded1251ab1fccfd69b058608f38f7a8-X," + `
            "FLUTTERWAVE_SECRET_KEY=FLWSECK-2d9e29e2c7e85214e55fa642cff59b99-19b9abc3310vt-X," + `
            "FLUTTERWAVE_ENCRYPTION_KEY=2d9e29e2c7e8eaa49db18d1b"

gcloud run deploy $SERVICE_NAME `
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME `
  --platform managed `
  --region $REGION `
  --project $PROJECT_ID `
  --allow-unauthenticated `
  --set-env-vars $ENV_VARS `
  --memory 2Gi `
  --cpu 2

Write-Host "✅ Deployment complete!" -ForegroundColor Green
# Read-Host "Press Enter to exit..."
