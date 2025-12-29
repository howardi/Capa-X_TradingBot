# Capa-X Trading Bot 🤖📈

**Professional Grade Multi-Market Algorithmic Trading System**

Capa-X is an advanced, AI-powered trading bot designed for institutional-grade performance across Crypto CEX (Centralized Exchanges) and DEX (Decentralized Exchanges). It features a unique 4-mode architecture allowing for safe simulation, secure proxy routing, direct high-frequency execution, and Web3 integration.

---

## 🌟 Key Features

### 1. Multi-Mode Trading Environments
*   **🟢 Demo Mode**: Risk-free paper trading with simulated balances. Perfect for strategy testing and validation without capital exposure.
*   **🛡️ CEX Proxy Mode**: Secure traffic routing for restricted regions (e.g., accessing global exchanges via proxy). Maintains a separate risk profile.
*   **⚡ CEX Direct Mode**: Direct API connection for minimum latency execution (Binance, Bybit, etc.).
*   **🦄 DEX Mode (Web3)**: On-chain trading via smart contracts (Uniswap/PancakeSwap) with gas optimization and wallet integration.

### 2. AI & Machine Learning Core
*   **🧠 CapaX Brain**: Ensemble model combining LSTM (Long Short-Term Memory), Transformers, and Reinforcement Learning (PPO).
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

## 🚀 Quick Start

### Prerequisites
*   **Python 3.9+**
*   **Node.js** (optional, for specific plugins)
*   **Docker** (recommended for production deployment)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/howardi/Capa-X_TradingBot.git
    cd Capa-X_TradingBot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**
    Create a `.env` file in the root directory. You can copy the structure below:
    ```env
    # --- Exchange Keys (Required for CEX) ---
    BINANCE_API_KEY=your_binance_key
    BINANCE_SECRET=your_binance_secret
    BYBIT_API_KEY=your_bybit_key
    BYBIT_SECRET=your_bybit_secret

    # --- Web3 (Required for DEX) ---
    WALLET_ADDRESS=0xYourWalletAddress...
    PRIVATE_KEY=your_private_key
    INFURA_URL=https://mainnet.infura.io/v3/your_infura_key

    # --- Proxy Settings (Optional) ---
    PROXY_URL=http://user:pass@host:port

    # --- General ---
    TRADING_MODE=Demo  # Options: Demo, CEX_Proxy, CEX_Direct, DEX
    ```

### Running the Bot

**1. Launch the Dashboard (UI)**
This is the primary way to interact with the bot. It launches a web interface to view charts, logs, and controls.
```bash
streamlit run dashboard.py
```

**2. Run Headless (CLI)**
For server deployments without a UI, or for background execution.
```bash
python main.py
```
*(Note: Ensure `main.py` is configured to your desired mode)*

**3. Run System Checks**
Verify all connections, API keys, and logic before deploying real capital.
```bash
python system_check.py
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

## 📦 Deployment

### Docker (Recommended)
Run the bot 24/7 using Docker Compose. This ensures all dependencies and the environment are consistent.
```bash
docker-compose up -d --build
```
*Supports platforms like Railway, Render, and VPS providers.*

### Vercel Deployment
*   **Status Page Only**: The Vercel configuration in this repo deploys a lightweight API Status Page.
*   **Limitation**: The full trading bot **cannot** run on Vercel Serverless due to timeout (10s) and memory limits.
*   See `DEPLOY.md` for full deployment details.

---

## ⚠️ Disclaimer
*This software is for educational purposes only. Cryptocurrency trading involves high risk of financial loss. The developers are not responsible for any financial losses incurred while using this bot. Always test in **Demo Mode** first.*

---

*Built with ❤️ by [Howard](https://github.com/howardi)*
