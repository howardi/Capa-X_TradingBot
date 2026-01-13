Write-Host "Starting CapaRox Trading Bot (Local Production)..." -ForegroundColor Cyan

# Set Environment Variables
$env:FRONTEND_DIST = "$PSScriptRoot\frontend\dist"
$env:DB_PATH = "$PSScriptRoot\users.db"
$env:PORT = "8080"
$env:FLASK_ENV = "production"

# Ensure frontend is built
if (-not (Test-Path "$env:FRONTEND_DIST")) {
    Write-Host "Frontend build not found. Building..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    npm run build
    Pop-Location
} else {
    Write-Host "✅ Frontend build found." -ForegroundColor Green
}

Write-Host "🚀 Launching Server..." -ForegroundColor Cyan
python serve.py
