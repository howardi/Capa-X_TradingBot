# Setup Script for GitHub Actions CI/CD
# This script creates a Service Account and generates the JSON key needed for GitHub Secrets.

Write-Host "🚀 Setting up GitHub Actions CI/CD credentials..." -ForegroundColor Cyan

# 1. Check Gcloud
if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ gcloud not found. Please install Google Cloud SDK." -ForegroundColor Red
    exit 1
}

# 2. Get Project ID
$PROJECT_ID = gcloud config get-value project 2>$null
if ([string]::IsNullOrWhiteSpace($PROJECT_ID) -or $PROJECT_ID -eq '(unset)') {
    $PROJECT_ID = Read-Host "Enter your Google Cloud Project ID"
}

if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
    Write-Host "❌ No Project ID. Exiting." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Using Project: $PROJECT_ID" -ForegroundColor Green

# 3. Create Service Account
$SA_NAME = "github-deployer"
$SA_EMAIL = "$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

Write-Host "Creating Service Account: $SA_NAME..." -ForegroundColor Yellow
gcloud iam service-accounts create $SA_NAME --display-name "GitHub Actions Deployer" --project $PROJECT_ID 2>$null

# 4. Grant Permissions
Write-Host "Granting permissions..." -ForegroundColor Yellow
$ROLES = @(
    "roles/run.admin",
    "roles/storage.admin",
    "roles/iam.serviceAccountUser",
    "roles/cloudbuild.builds.editor"
)

foreach ($role in $ROLES) {
    gcloud projects add-iam-policy-binding $PROJECT_ID `
        --member "serviceAccount:$SA_EMAIL" `
        --role $role `
        --condition=None `
        --quiet > $null
}

# 5. Generate Key
Write-Host "Generating key file..." -ForegroundColor Yellow
$KEY_FILE = "gcp_key.json"
if (Test-Path $KEY_FILE) { Remove-Item $KEY_FILE }

gcloud iam service-accounts keys create $KEY_FILE `
    --iam-account $SA_EMAIL `
    --project $PROJECT_ID

Write-Host "`n✅ SUCCESS! Service Account configured." -ForegroundColor Green
Write-Host "---------------------------------------------------"
Write-Host "PLEASE ADD THE FOLLOWING SECRETS TO YOUR GITHUB REPO:"
Write-Host "Settings > Secrets and variables > Actions > New repository secret"
Write-Host "---------------------------------------------------"
Write-Host "1. Name: GCP_CREDENTIALS"
Write-Host "   Value: (Copy the content of $KEY_FILE)"
Write-Host ""
Write-Host "2. Other Secrets (from your local config or .env):"
Write-Host "   - FLUTTERWAVE_PUBLIC_KEY"
Write-Host "   - FLUTTERWAVE_SECRET_KEY"
Write-Host "   - FLUTTERWAVE_ENCRYPTION_KEY"
Write-Host "   - BINANCE_API_KEY"
Write-Host "   - BINANCE_SECRET"
Write-Host "   - BYBIT_API_KEY"
Write-Host "   - BYBIT_SECRET"
Write-Host "---------------------------------------------------"
Write-Host "⚠️  WARNING: Delete $KEY_FILE after adding it to GitHub Secrets!"
