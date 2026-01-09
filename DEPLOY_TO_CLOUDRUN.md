# Deploying CapaRox Trading Bot to Google Cloud Run

Since this is a trading bot, you want it to run 24/7 without your computer being on. Google Cloud Run is a great choice for this.

## ⚠️ Important Note on Data
Google Cloud Run is **stateless**. This means that if the application restarts (which happens automatically for updates or inactivity), **files saved locally (like `trading_bot.db`) will be reset**.
To keep your trading history and balances persistent, you would typically need to connect to an external database (like Google Cloud SQL) or use a volume (which might cost money).
**For the Free Tier setup below, be aware that your trade history might clear on restart.**

## Prerequisites
1. A Google Cloud Platform (GCP) Account (Free).
2. A Project created in GCP.

## Steps to Deploy

### Option 1: Direct Upload (Easiest)

1. **Go to Google Cloud Run Console**: https://console.cloud.google.com/run
2. Click **"Create Service"**.
3. **Source**: Select **"Continuously deploy new revisions from a source repository"** if you have this on GitHub.
   * *OR* if you don't use GitHub: Select **"Deploy one revision from an existing container image"** (Requires building the image first, which is complex without CLI).
   
   **Better Path for "No CLI":**
   Use the **Cloud Shell** in the browser (Top right terminal icon in GCP Console).

4. **Using Cloud Shell (Recommended)**:
   * Open Cloud Shell in your browser.
   * Upload this entire folder to Cloud Shell (Three dots menu > Upload).
   * Run the following command in Cloud Shell:
     ```bash
     gcloud run deploy caparox-bot --source . --allow-unauthenticated --region us-central1
     ```
   * When asked for "service name", press Enter.
   * When asked to enable APIs, say **y**.

5. **Wait for Deployment**:
   * It will build the container and deploy it.
   * Once done, it will give you a **Service URL** (e.g., `https://caparox-bot-xyz.a.run.app`).
   * This link is permanent and SSL-secured.

### Option 2: Install gcloud CLI locally
1. Install Google Cloud SDK on your computer.
2. Run `gcloud auth login`.
3. Run `gcloud run deploy caparox-bot --source . --allow-unauthenticated` from this folder.

## Configuration
- **Port**: The Dockerfile is configured to listen on the `$PORT` environment variable (defaults to 8080), which Cloud Run automatically sets.
- **Memory**: You might need to increase memory to 1GB or 2GB in the "Edit & Deploy New Revision" settings if the app crashes (Streamlit + ML libs can be heavy).
