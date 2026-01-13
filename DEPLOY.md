# Deployment Instructions for Google Cloud Run

Your application is ready for deployment. The frontend has been built and the backend is configured.

## Prerequisites
- Google Cloud SDK (gcloud CLI) installed and authenticated.
- Docker installed (optional, for local testing).

## Steps to Deploy

1. **Build the Docker Image**
   Run the following command in your terminal (from the project root):
   ```bash
   gcloud builds submit --tag gcr.io/[PROJECT-ID]/caparox-bot
   ```
   Replace `[PROJECT-ID]` with your actual Google Cloud Project ID.

2. **Deploy to Cloud Run (with Database)**
   To ensure data persistence, you should connect the application to a managed PostgreSQL database (Cloud SQL).

   **Option A: Quick Start (Ephemeral / Testing)**
   (Data will be lost on restart)
   ```bash
   gcloud run deploy caparox-bot \
     --image gcr.io/[PROJECT-ID]/caparox-bot \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 1Gi
   ```

   **Option B: Production (Persistent Database)**
   1. Create a Cloud SQL instance (PostgreSQL) in Google Cloud Console.
   2. Create a database (e.g., `caparox_db`) and a user.
   3. Get the **Connection Name** (e.g., `project-id:region:instance-name`).
   4. Deploy with the database connection:
      ```bash
      gcloud run deploy caparox-bot \
        --image gcr.io/[PROJECT-ID]/caparox-bot \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --memory 1Gi \
        --add-cloudsql-instances [CONNECTION_NAME] \
        --set-env-vars "DATABASE_URL=postgresql+psycopg2://[USER]:[PASSWORD]@/[DB_NAME]?host=/cloudsql/[CONNECTION_NAME]"
      ```
      Replace `[USER]`, `[PASSWORD]`, `[DB_NAME]`, and `[CONNECTION_NAME]` with your actual values.

## Local Testing with Docker (Optional)
If you have Docker installed, you can test the full container locally before deploying:

1. Build:
   ```bash
   docker build -t caparox-bot .
   ```

2. Run:
   ```bash
   docker run -p 8080:8080 -e PORT=8080 caparox-bot
   ```
   Then verify at `http://localhost:8080`.

## Notes
- **Database**: The application automatically detects if `DATABASE_URL` is set.
  - If set, it connects to PostgreSQL.
  - If not set, it falls back to a local SQLite file (`users.db`).
