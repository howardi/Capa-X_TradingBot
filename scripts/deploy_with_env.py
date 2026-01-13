import os
import subprocess
import sys

def get_gcloud_project():
    try:
        # Get the current active project
        project = subprocess.check_output(
            "gcloud config get-value project", 
            shell=True,
            text=True
        ).strip()
        return project
    except Exception as e:
        print(f"Error getting gcloud project: {e}")
        return None

def load_env_file(filepath):
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def deploy():
    project_id = get_gcloud_project()
    if not project_id:
        print("❌ Could not determine Google Cloud Project ID. Please run 'gcloud config set project [PROJECT_ID]'.")
        return

    service_name = "caparox-bot"
    region = "us-central1"
    
    print(f"🚀 Preparing deployment for project: {project_id}")

    # Load .env
    env_vars = load_env_file('.env')
    
    # Check for Database Config
    db_url = env_vars.get('DATABASE_URL')
    cloud_sql_instance = env_vars.get('CLOUDSQL_INSTANCE')
    
    if not db_url or not cloud_sql_instance:
        print("\n⚠️  WARNING: Persistent Database Configuration Missing!")
        print("   To enable Cloud SQL (PostgreSQL), ensure your .env file contains:")
        print("     DATABASE_URL=postgresql+psycopg2://USER:PASS@/DB_NAME?host=/cloudsql/INSTANCE_CONNECTION_NAME")
        print("     CLOUDSQL_INSTANCE=INSTANCE_CONNECTION_NAME")
        print("   Deploying in EPHEMERAL mode (SQLite). Data will be lost on restart.\n")
    else:
        print("✅ Persistent Database Configuration Found.")

    # Construct env vars string for gcloud
    env_list = []
    for k, v in env_vars.items():
        if k == 'CLOUDSQL_INSTANCE': continue # This is handled via flag, but keeping it in env is fine too.
        env_list.append(f"{k}={v}")
    
    env_string = ",".join(env_list)
    
    # 1. Build
    print("🔨 Building container...")
    try:
        subprocess.run(f"gcloud builds submit --tag gcr.io/{project_id}/{service_name}", shell=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Build failed.")
        return

    # 2. Deploy
    print("☁️ Deploying service...")
    cmd_str = f"gcloud run deploy {service_name} --image gcr.io/{project_id}/{service_name} --platform managed --region {region} --allow-unauthenticated"
    
    if env_string:
        # Quote the env string to handle special chars
        cmd_str += f' --set-env-vars "{env_string}"'
        
    if cloud_sql_instance:
        cmd_str += f' --add-cloudsql-instances {cloud_sql_instance}'
        
    print(f"Running: {cmd_str}")
    subprocess.run(cmd_str, shell=True)

if __name__ == "__main__":
    deploy()
