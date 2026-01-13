# Deployment Guide for CapaRox Trading Bot

This guide covers how to deploy the CapaRox Trading Bot to the cloud. The application is containerized using Docker, making it easy to deploy to platforms like Google Cloud Run, AWS App Runner, Heroku, or a generic VPS.

## Prerequisites

- **Docker** installed on your machine.
- A **Cloud Provider Account** (Google Cloud, AWS, DigitalOcean, etc.).
- **Git** (optional but recommended).

## 1. Environment Configuration

Before deploying, you must configure your environment variables.
In the cloud, you typically set these in the dashboard of your provider.

**Required Variables:**
- `SECRET_KEY`: A long random string for session security.
- `DATABASE_URL`: Connection string for your production database (PostgreSQL recommended).
  - Example: `postgresql://user:password@hostname:5432/dbname`
  - For Google Cloud SQL: `postgresql://user:password@/dbname?host=/cloudsql/project:region:instance`
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`: For sending password reset emails.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: For Google OAuth.
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`: For GitHub OAuth.
- `FRONTEND_URL`: The URL where your frontend is hosted (e.g., `https://your-app.com`).
- `ADMIN_SECRET`: A secret string to protect the admin user list endpoint.

## 2. Deploying with Docker (Universal)

You can build and run the image anywhere Docker is supported.

### Build the Image
```bash
docker build -t caparox-bot .
```

### Run Locally (for testing)
```bash
docker run -p 5000:5000 --env-file .env caparox-bot
```

## 3. Deploying to Google Cloud Run (Recommended)

Since your configuration hinted at Google Cloud SQL, Cloud Run is a great serverless option.

1.  **Install Google Cloud SDK** and login:
    ```bash
    gcloud auth login
    gcloud config set project YOUR_PROJECT_ID
    ```

2.  **Build and Push to Container Registry**:
    ```bash
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/caparox-bot
    ```

3.  **Deploy to Cloud Run**:
    ```bash
    gcloud run deploy caparox-bot \
      --image gcr.io/YOUR_PROJECT_ID/caparox-bot \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --add-cloudsql-instances YOUR_CLOUDSQL_INSTANCE_CONNECTION_NAME \
      --set-env-vars "DATABASE_URL=postgresql://user:pass@/dbname?host=/cloudsql/INSTANCE_NAME,SECRET_KEY=supersecret,..."
    ```

## 4. Database Migrations

The application automatically initializes the database tables (`init_db()`) on startup if they don't exist.
Ensure your `DATABASE_URL` points to a valid PostgreSQL database.

## 5. Admin Access

To view registered users, you can access the admin endpoint.
Since there is no UI for this yet, you can use `curl` or Postman:

```bash
curl -H "X-Admin-Secret: YOUR_ADMIN_SECRET" https://your-app-url.com/api/admin/users
```

## 6. Features Checklist

- [x] **Bot Trading**: Automated trading logic with risk management.
- [x] **Wallet**: EVM, Tron, TON wallet generation and transfers.
- [x] **Auth**: Register, Login, OAuth (Google/GitHub), Password Reset.
- [x] **Admin**: User list access.
- [x] **Cloud Ready**: Dockerfile and Procfile included.

## Troubleshooting

- **Database Connection**: If using Cloud SQL, ensure the service account has "Cloud SQL Client" role.
- **Email Sending**: If emails aren't arriving, check `SMTP_` variables. The logs will show "MOCK EMAIL" if not configured.
- **TON Support**: Requires `tonsdk` (installed). Note that USDT on TON (Jetton) automated transfer is currently limited; native TON transfer works.
