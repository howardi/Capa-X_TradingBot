# Helper script to build and test the CapaRox Bot Docker image

Write-Host "--- CapaRox Bot Deployment Helper ---" -ForegroundColor Cyan

# 1. Check for Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop."
    exit 1
}

# 2. Build Image
Write-Host "Building Docker Image (caparox-bot)..." -ForegroundColor Yellow
docker build -t caparox-bot .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build Successful!" -ForegroundColor Green
    Write-Host "You can now run the bot locally with:" -ForegroundColor Gray
    Write-Host "docker run -p 5000:5000 --env-file .env caparox-bot" -ForegroundColor White
    
    Write-Host "`nTo push to cloud, tag and push this image to your registry (e.g., GCR, ECR, Docker Hub)." -ForegroundColor Gray
} else {
    Write-Error "Build Failed. Check the error messages above."
    exit 1
}
