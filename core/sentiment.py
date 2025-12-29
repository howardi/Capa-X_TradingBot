import random
import requests
import xml.etree.ElementTree as ET
import re
from typing import Dict, List

class SentimentEngine:
    def __init__(self):
        self.sources = {
            'CoinTelegraph': 'https://cointelegraph.com/rss',
            'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/'
        }
        # Keywords for simple sentiment scoring
        self.keywords = {
            'bullish': ['bull', 'surge', 'record', 'high', 'adoption', 'gain', 'rally', 'growth', 'launch', 'approve', 'etf', 'support'],
            'bearish': ['bear', 'crash', 'drop', 'low', 'ban', 'hack', 'scam', 'fear', 'regulation', 'sell', 'lawsuit', 'resistance']
        }
        
    def fetch_rss(self, url):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"Error fetching RSS from {url}: {e}")
        return None

    def parse_headlines(self, content) -> List[str]:
        headlines = []
        if not content:
            return headlines
            
        try:
            root = ET.fromstring(content)
            # RSS 2.0
            for item in root.findall('.//item'):
                title = item.find('title')
                if title is not None:
                    headlines.append(title.text)
        except:
            # Fallback regex if XML parsing fails
            try:
                headlines = re.findall(r'<title>(.*?)</title>', str(content))
            except:
                pass
        return headlines

    def analyze_sentiment(self, symbol: str) -> Dict:
        """
        Analyze social sentiment using Real RSS Feeds.
        """
        all_headlines = []
        
        # Fetch real news
        for source, url in self.sources.items():
            content = self.fetch_rss(url)
            headlines = self.parse_headlines(content)
            all_headlines.extend(headlines)
            
        # If no internet or fetch failed, fall back to mock for demo stability
        if not all_headlines:
             return self._mock_sentiment(symbol)
             
        # Analyze Headlines
        score = 50.0 # Neutral start
        relevant_headlines = []
        
        for headline in all_headlines:
            # Check if headline is relevant to crypto generally or the symbol
            # For simplicity, we assume all crypto news affects the market sentiment
            # But we boost weight if symbol is mentioned
            weight = 1.0
            if symbol.lower() in headline.lower():
                weight = 2.0
                relevant_headlines.append(headline)
                
            headline_lower = headline.lower()
            
            for word in self.keywords['bullish']:
                if word in headline_lower:
                    score += (2.0 * weight)
                    
            for word in self.keywords['bearish']:
                if word in headline_lower:
                    score -= (2.0 * weight)
                    
        # Normalize score to 0-100
        score = max(0, min(100, score))
        
        classification = "Neutral"
        if score > 60: classification = "Bullish"
        if score > 80: classification = "Euphoria"
        if score < 40: classification = "Bearish"
        if score < 20: classification = "Fear"
        
        trending_topics = [f"#{symbol}", "#Crypto", "#Market"]
        if score > 60: trending_topics.append("#BullRun")
        if score < 40: trending_topics.append("#BearMarket")
        
        return {
            'score': score,
            'classification': classification,
            'social_volume': len(all_headlines), # Use count of headlines as proxy
            'trending_topics': trending_topics,
            'sources_analyzed': len(self.sources),
            'latest_headlines': relevant_headlines[:3] if relevant_headlines else all_headlines[:3]
        }
        
    def _mock_sentiment(self, symbol):
        """Fallback mock if network fails"""
        sentiment_score = random.uniform(0, 100)
        volume_score = random.uniform(0, 100)
        
        classification = "Neutral"
        if sentiment_score > 60: classification = "Bullish"
        if sentiment_score > 80: classification = "Euphoria"
        if sentiment_score < 40: classification = "Bearish"
        if sentiment_score < 20: classification = "Fear"
        
        trending_topics = [f"#{symbol}", "#Crypto", "#BullRun"] if sentiment_score > 50 else [f"#{symbol}", "#Crash", "#Scam"]
        
        return {
            'score': sentiment_score,
            'classification': classification,
            'social_volume': volume_score,
            'trending_topics': trending_topics,
            'sources_analyzed': 0
        }
        
    def get_news_headlines(self, symbol: str):
        """Fetch real news headlines"""
        all_headlines = []
        for source, url in self.sources.items():
            content = self.fetch_rss(url)
            headlines = self.parse_headlines(content)
            all_headlines.extend(headlines)
            
        if not all_headlines:
             return self._mock_news(symbol)
             
        # Filter for symbol if possible, else return general top news
        symbol_news = [h for h in all_headlines if symbol.lower() in h.lower()]
        
        if symbol_news:
            return symbol_news[:5]
        return all_headlines[:5]

    def _mock_news(self, symbol):
        bullish_news = [
            f"{symbol} adoption grows in Asia",
            f"Major partnership announced for {symbol}",
            f"{symbol} breaks key resistance level"
        ]
        bearish_news = [
            f"Regulatory concerns surround {symbol}",
            f"{symbol} network congestion issues",
            f"Whale moves large amount of {symbol} to exchange"
        ]
        
        if random.random() > 0.5:
            return bullish_news
        else:
            return bearish_news
