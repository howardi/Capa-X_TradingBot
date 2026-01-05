# CapacityBay Trading Bot 🤖📈

**Professional Grade Multi-Market Algorithmic Trading System**

CapacityBay is an advanced, AI-powered trading bot designed for institutional-grade performance across Crypto CEX (Centralized Exchanges) and DEX (Decentralized Exchanges). It features a unique 4-mode architecture allowing for safe simulation, secure proxy routing, direct high-frequency execution, and Web3 integration.

---

## 🌟 Key Features

### 1. Multi-Mode Trading Environments
*   **🟢 Demo Mode**: Risk-free paper trading with simulated balances. Perfect for strategy testing and validation without capital exposure.
*   **🛡️ CEX Proxy Mode**: Secure traffic routing for restricted regions (e.g., accessing global exchanges via proxy). Maintains a separate risk profile.
*   **⚡ CEX Direct Mode**: Direct API connection for minimum latency execution (Binance, Bybit, etc.).
*   **🦄 DEX Mode (Web3)**: On-chain trading via smart contracts (Uniswap/PancakeSwap) with gas optimization and wallet integration.

### 2. AI & Machine Learning Core
*   **🧠 CapacityBay Brain**: Ensemble model combining LSTM (Long Short-Term Memory), Transformers, and Reinforcement Learning (PPO).
*   **📊 Sentiment Engine**: Real-time NLP analysis of news and social media to gauge market emotion.
*   **🔮 Quantum Features**: Experimental probability distribution modeling for extreme market events.

### 3. Adaptive Risk Management
*   **🛡️ Isolated Risk Profiles**: Separate drawdown limits, win/loss tracking, and stop-losses for each trading mode.
*   **⚖️ Dynamic Position Sizing**: Kelly Criterion-based allocation adjusted by market volatility and regime.
*   **🛑 Circuit Breakers**: Automatic trading halt upon breaching max daily loss thresholds.

### 4. Real-Time Dashboard
*   Built with **Streamlit** for monitoring PnL, active positions, and AI signals.
*   Visualizes model confidence, market regime classification, and live asset prices.

---

## 🚀 Quick Start (Local Python)

### Prerequisites
*   **Python 3.9+**
*   **Node.js** (optional, for specific plugins)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/howardi/CapacityBay_TradingBot.git
    cd CapacityBay_TradingBot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**
    Copy `.env.example` to `.env` and fill in your details:
    ```bash
    cp .env.example .env
    # Edit .env with your API Keys
    ```

4.  **Run the Bot**
    *   **UI Dashboard:** `streamlit run dashboard.py`
    *   **Trading Core:** `python main.py`

---

## 🐳 Docker / Local Live Trading (Recommended)

Running with Docker ensures the bot operates in an isolated, stable environment, identical to production servers. This is the **best method for live trading**.

### 1. Prerequisites
*   Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. Setup
1.  **Clone & Enter Directory:**
    ```bash
    git clone https://github.com/howardi/CapacityBay_TradingBot.git
    cd CapacityBay_TradingBot
    ```

2.  **Configure Environment:**
    Ensure your `.env` file is created and populated with valid API keys (see `.env.example`).
    ```bash
    # Windows
    copy .env.example .env
    # Linux/Mac
    cp .env.example .env
    ```

### 3. Run Commands
Start the entire system (Trading Core + Dashboard + Redis) in the background:
```bash
docker-compose up -d --build
```

### 4. Monitor
*   **View Dashboard:** Open `http://localhost:8501` in your browser.
*   **View Trading Logs:**
    ```bash
    docker-compose logs -f trading-bot
    ```
*   **Stop System:**
    ```bash
    docker-compose down
    ```

---

## 🛠️ Architecture Overview

The bot is modularized into `core/` components:

*   **`core/bot.py`**: Central controller managing the main loop and mode switching.
*   **`core/strategies.py`**: Implementation of trading strategies (`SniperStrategy`, `MeanReversion`, etc.).
*   **`core/risk.py`**: `AdaptiveRiskManager` enforcing drawdown limits and position sizing.
*   **`core/execution.py`**: Routing logic that directs orders to CCXT (CEX) or Web3 (DEX) based on the active mode.
*   **`core/data.py`**: Unified data fetcher with proxy support and OHLCV standardization.
*   **`core/brain.py`**: The AI inference engine.

---

## 📦 Cloud Deployment

### Railway / Render (Production)
1.  Fork this repo.
2.  Connect to Railway/Render.
3.  Add Environment Variables (copy from your `.env`).
4.  Deploy! (The `Dockerfile` handles the rest).

### Vercel (Monitor Only)
*   **Status Page Only**: The Vercel configuration deploys a lightweight API Status Page.
*   **Limitation**: The full trading bot **cannot** run on Vercel Serverless.
*   See `DEPLOY.md` for full deployment details.

---

## ⚠️ Disclaimer
*This software is for educational purposes only. Cryptocurrency trading involves high risk of financial loss. The developers are not responsible for any financial losses incurred while using this bot. Always test in **Demo Mode** first.*

---

*Built with ❤️ by [Howard](https://github.com/howardi)*
