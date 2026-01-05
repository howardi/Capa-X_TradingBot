# Deployment Guide

## 🚀 Recommended Deployment (Docker)

For the full functionality of **CapacityBay Trading Bot**, including the AI engine, continuous trading loop, and real-time dashboard, you **must** use a platform that supports persistent Docker containers.

### Option 1: Railway / Render (Easiest)
1. Fork this repository.
2. Connect your GitHub to [Railway](https://railway.app) or [Render](https://render.com).
3. Select this repository.
4. The platform will automatically detect the `Dockerfile` and build the bot.
   - **Note:** Ensure you set your environment variables (API keys, etc.) in the platform's dashboard.

### Option 2: VPS (Advanced)
1. SSH into your server.
2. Clone the repo:
   ```bash
   git clone https://github.com/howardi/CapacityBay_TradingBot.git
    cd CapacityBay_TradingBot
   ```
3. Run with Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

---

## ⚡ Vercel Deployment (Limited)

**Note:** Vercel is designed for static sites and serverless functions. It **cannot** run the continuous trading loop or the heavy AI models (Torch/TensorFlow) due to size and timeout limits.

The Vercel configuration in this repo deploys a lightweight **API Status Page** only.

1. Connect your GitHub repo to [Vercel](https://vercel.com).
2. Vercel will detect `vercel.json` and deploy the API.
3. Access your deployment to see the status message.

**Warning:** Do not attempt to run the full `dashboard.py` or `bot.py` on Vercel; the build will fail.
