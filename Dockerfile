FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# Note: ./vendor/pandas_ta must be present in the build context
COPY vendor/ ./vendor/
RUN pip3 install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["streamlit", "run", "dashboard_impl.py", "--server.port=8080", "--server.address=0.0.0.0"]
