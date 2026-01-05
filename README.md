# CapacityBay Trading Bot 🤖📈

Institutional‑grade, AI‑powered trading across CEX and DEX with elite risk controls, optimizer mode, and transparent, audit‑friendly execution.

---

## 🌟 Highlights

- Multi‑mode trading: `Demo`, `CEX_Proxy`, `CEX_Direct`, `DEX` with isolated risk per mode.
- Optimizer Mode selects the best strategy per regime and scales position size by allocation weights.
- Strict risk controls: dynamic confidence gating, regime‑aware cooldowns, kill‑switches, portfolio limits.
- Profit protection: breakeven, ATR trailing with Chandelier Exit, multi‑target partial take‑profits.
- Full audit trail: pre‑trade explanation logged with strategy, regime, entry, SL/TP, size, confidence.

---

## 🚀 Quick Start (Local)

- Python 3.9+
- Clone, install, configure, run:
  - `git clone https://github.com/howardi/Capa-X_TradingBot.git && cd Capa-X_TradingBot`
  - `pip install -r requirements.txt`
  - Copy `.env.example` to `.env` and set your keys
  - Dashboard: `streamlit run dashboard.py`
  - Core loop: `python main.py`

---

## 🐳 Docker (Recommended)

- `docker-compose up -d --build`
- Dashboard: `http://localhost:8501`
- Logs: `docker-compose logs -f trading-bot`
- Stop: `docker-compose down`

---

## 🧠 Strategies & Optimizer

- Strategies: Smart Trend, Sniper, Weighted Ensemble, Liquidity Sweep, Order Flow, Swing Range.
- Optimizer Mode: selects the best strategy per regime and scales size by weights.
  - Code: `core/bot.py:844` chooses strategy using `self.profit_optimizer.get_allocation_weights` and applies `allocation_weight` to `position_size` in `core/bot.py:866–871`.
  - Default mode: `core/bot.py:99` sets `"Profit Optimization Layer"` as the active mode.

---

## 🛡️ Risk & Execution Discipline

- Dynamic confidence threshold:
  - Base from `config/trading_config.py:27–30`, auto‑raises with drawdown and loss streaks.
  - Gate: `core/bot.py:936–941` skips execution if `signal.confidence` < threshold.
- Regime‑aware cooldown:
  - `core/bot.py:921–926` applies 20 min in volatile regimes, else 15 min; bypass only for very high confidence (≥ 0.85).
- Kill‑switch and portfolio limits:
  - Kill‑switch: `core/bot.py:929–933` halts during drawdowns.
  - Limits: `core/bot.py:959–965` blocks trades exceeding exposure.
- Sanity checks and pre‑trade explanation:
  - Valid levels/size: `core/bot.py:966–970`.
  - Explanation string: `core/bot.py:972–978`; logged in `core/bot.py:616–630`.

---

## 🎯 Profit Protection

- Breakeven after 1R and ATR trailing:
  - `core/bot.py:742–753` (long) and `core/bot.py:755–764` (short).
- Chandelier Exit integration:
  - `core/bot.py:750–753` for long; `core/bot.py:761–764` for short.
- Multi‑target partials:
  - TP1 50% at 1.5R: `core/bot.py:766–787`.
  - TP2 50% of remaining at 2.5R: `core/bot.py:787–803`.

---

## 📊 Dashboard & Monitor

- Local Streamlit dashboard: `dashboard.py` at `http://localhost:8501`.
- Vercel Lite Monitor: public status at `/` and `/status`, authenticated demo dashboard at `/dashboard`.
- Features (Lite): exchange health pings, latency chart, auto‑refresh price, multi‑asset demo trading.
- Demo trading: percent‑mode SL/TP, R‑multiple TP presets, trailing stop, breakeven, flatten positions.
- Auth (Lite): access code `admin` sets `capax_auth` cookie for `/dashboard`.
- Routing: `vercel.json` routes all to `api/index.py`.

---

## 📦 Deployment

- Railway/Render (full bot with Docker): see `DEPLOY.md`.
- Vercel (Lite monitor): deploy `api/index.py` with `@vercel/python`.
  - Ensure `vercel.json` exists.
  - Connect repository to Vercel for auto‑deploy on `git push`.
  - Or use CLI: `vercel --prod`.
  - Note: Lite monitor does not run the full trading loop; for 24/7 trading use Docker.

---

## Configuration Tips

- Confidence floor: `config/trading_config.py:27–30` (`min_confidence_threshold`).
- Asset/timeframe defaults: `config/settings.py`.
- Risk sizing, kill‑switch, volatility handling: `core/risk.py`.

---

## Disclaimer

This software is for educational purposes only. Trading involves significant risk. Use Demo Mode first.

---

Built with ❤️ by [Howard](https://github.com/howardi)
