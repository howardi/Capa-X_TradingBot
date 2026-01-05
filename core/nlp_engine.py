
import re

class NLPEngine:
    """
    Natural Language Processing Engine for the 'CapacityBay Assistant'.
    Parses user text/voice commands into executable bot actions.
    """
    def __init__(self, bot):
        self.bot = bot
        
    def parse_command(self, text):
        """
        Convert natural language to action.
        """
        text = text.lower().strip()
        
        response = {
            "action": None,
            "params": {},
            "reply": "I didn't understand that command. Try 'Price of BTC' or 'Buy 0.1 ETH'."
        }
        
        # 1. Trading Commands
        # "Buy 0.1 BTC", "Long 100 ETH"
        match_buy = re.search(r"(buy|long)\s+(\d+\.?\d*)\s*([a-z]+)", text)
        if match_buy:
            amount = float(match_buy.group(2))
            asset = match_buy.group(3).upper()
            # Normalize symbol (simple guess)
            symbol = f"{asset}/USDT"
            
            response["action"] = "trade"
            response["params"] = {"side": "buy", "amount": amount, "symbol": symbol}
            response["reply"] = f"Preparing to BUY {amount} {symbol}..."
            return response

        match_sell = re.search(r"(sell|short)\s+(\d+\.?\d*)\s*([a-z]+)", text)
        if match_sell:
            amount = float(match_sell.group(2))
            asset = match_sell.group(3).upper()
            symbol = f"{asset}/USDT"
            
            response["action"] = "trade"
            response["params"] = {"side": "sell", "amount": amount, "symbol": symbol}
            response["reply"] = f"Preparing to SELL {amount} {symbol}..."
            return response
            
        # 2. System Commands
        if "stop" in text and ("bot" in text or "trading" in text):
            response["action"] = "system"
            response["params"] = {"command": "stop"}
            response["reply"] = "Stopping all trading activities immediately."
            return response
            
        if "start" in text and ("bot" in text or "trading" in text):
            response["action"] = "system"
            response["params"] = {"command": "start"}
            response["reply"] = "Resuming trading operations."
            return response
            
        if "risk" in text:
            # "Set risk to 1%"
            match_risk = re.search(r"risk.*(\d+\.?\d*)%", text)
            if match_risk:
                val = float(match_risk.group(1))
                response["action"] = "config"
                response["params"] = {"key": "risk", "value": val}
                response["reply"] = f"Setting risk per trade to {val}%."
                return response
                
        # 3. Query Commands
        if "price" in text:
            # "Price of BTC"
            match_asset = re.search(r"price.*of\s+([a-z]+)", text)
            asset = match_asset.group(1).upper() if match_asset else self.bot.symbol.split('/')[0]
            symbol = f"{asset}/USDT"
            
            response["action"] = "query"
            response["params"] = {"type": "price", "symbol": symbol}
            response["reply"] = f"Checking price for {symbol}..."
            return response
            
        if "sentiment" in text:
            response["action"] = "query"
            response["params"] = {"type": "sentiment"}
            response["reply"] = "Analyzing market sentiment..."
            return response
            
        if "status" in text or "report" in text:
            response["action"] = "query"
            response["params"] = {"type": "status"}
            response["reply"] = "Compiling status report..."
            return response
            
        if "switch" in text or "strategy" in text:
            # "Switch to Grid Trading"
            strategies = ["Smart Trend", "Grid Trading", "Mean Reversion", "Funding Arbitrage", "Basis Trade", "Liquidity Sweep", "Order Flow"]
            for s in strategies:
                if s.lower() in text:
                    response["action"] = "config"
                    response["params"] = {"key": "strategy", "value": s}
                    response["reply"] = f"Switching strategy to {s}..."
                    return response
            
        return response

    def process_query(self, text, user_manager=None):
        """
        Execute the parsed command and return a response.
        """
        cmd = self.parse_command(text)
        
        if cmd['action'] == 'query':
            if cmd['params'].get('type') == 'price':
                symbol = cmd['params']['symbol']
                try:
                    ticker = self.bot.data_manager.fetch_ticker(symbol)
                    price = ticker.get('last', 'Unknown')
                    return f"💰 The price of **{symbol}** is **${price}**."
                except Exception as e:
                    return f"❌ Error fetching price: {str(e)}"
                    
            elif cmd['params'].get('type') == 'sentiment':
                sent = self.bot.fundamentals.get_market_sentiment()
                score = sent.get('score', 0)
                mood = "Bullish 🚀" if score > 20 else "Bearish 🐻" if score < -20 else "Neutral 😐"
                return f"🧠 Market Sentiment: **{mood}** (Score: {score})"
                
            elif cmd['params'].get('type') == 'status':
                pnl = 0
                if user_manager:
                    metrics = user_manager.get_performance_metrics()
                    pnl = metrics.get('total_pnl', 0)
                return f"📊 **Status Report**\nActive Strategy: {self.bot.active_strategy_name}\nPnL: ${pnl:.2f}\nMode: {self.bot.trading_mode}"
                
        elif cmd['action'] == 'config':
            if cmd['params'].get('key') == 'strategy':
                new_strat = cmd['params']['value']
                success = self.bot.set_strategy(new_strat)
                return f"✅ Strategy switched to **{new_strat}**." if success else "❌ Failed to switch strategy."
                
        elif cmd['action'] == 'trade':
             # In a real scenario, this would trigger the bot.execution engine
             # For safety in this demo, we'll just confirm intent
             return f"⚠️ **Trade Command Received**: {cmd['reply']}\n(Please confirm in manual terminal)"

        elif cmd['action'] == 'system':
            return f"⚙️ {cmd['reply']}"

        return cmd['reply']
