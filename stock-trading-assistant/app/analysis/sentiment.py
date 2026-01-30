"""
Sentiment analysis module for news and market sentiment
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)


# Simple sentiment word lists (in production, use NLP library or API)
POSITIVE_WORDS = {
    "beat", "beats", "exceeded", "exceeds", "upgrade", "upgraded", "upgrades",
    "buy", "bullish", "outperform", "strong", "growth", "profit", "profitable",
    "surge", "surges", "surged", "soar", "soars", "soared", "rally", "rallies",
    "gain", "gains", "gained", "rise", "rises", "rising", "rose", "positive",
    "optimistic", "record", "best", "breakthrough", "success", "successful",
    "expand", "expansion", "innovative", "innovation", "partnership", "deal",
    "acquisition", "dividend", "buyback", "repurchase", "beat expectations",
    "above estimates", "raised guidance", "increased guidance", "momentum",
}

NEGATIVE_WORDS = {
    "miss", "missed", "misses", "downgrade", "downgraded", "downgrades",
    "sell", "bearish", "underperform", "weak", "weakness", "loss", "losses",
    "decline", "declines", "declined", "drop", "drops", "dropped", "fall",
    "falls", "fell", "falling", "plunge", "plunges", "plunged", "crash",
    "negative", "pessimistic", "worst", "failure", "failed", "fails",
    "layoff", "layoffs", "restructuring", "bankruptcy", "default", "debt",
    "lawsuit", "investigation", "fraud", "scandal", "recall", "warning",
    "below estimates", "missed expectations", "lowered guidance", "cut",
    "concern", "concerns", "worried", "worry", "risk", "risks", "risky",
}

VERY_POSITIVE_WORDS = {
    "blockbuster", "blowout", "record-breaking", "all-time high",
    "massive growth", "extraordinary", "exceptional", "remarkable",
}

VERY_NEGATIVE_WORDS = {
    "bankrupt", "bankruptcy", "fraud", "criminal", "indicted",
    "collapse", "collapsed", "crisis", "disaster", "catastrophic",
}


def analyze_news_sentiment(news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze sentiment from news headlines
    
    Args:
        news_items: List of news items with 'title' field
    
    Returns:
        Dict with sentiment score and breakdown
    """
    if not news_items:
        return {
            "score": 50,  # Neutral if no news
            "sentiment": "neutral",
            "news_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "headlines": [],
        }
    
    sentiments = []
    analyzed_headlines = []
    
    for item in news_items:
        title = item.get("title", "").lower()
        sentiment_score = analyze_text_sentiment(title)
        sentiments.append(sentiment_score)
        
        analyzed_headlines.append({
            "title": item.get("title", ""),
            "sentiment_score": sentiment_score,
            "published": item.get("published"),
            "publisher": item.get("publisher", ""),
        })
    
    # Calculate average sentiment
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 50
    
    # Count positive/negative
    positive_count = sum(1 for s in sentiments if s > 55)
    negative_count = sum(1 for s in sentiments if s < 45)
    
    # Determine overall sentiment label
    if avg_sentiment >= 65:
        sentiment_label = "very_positive"
    elif avg_sentiment >= 55:
        sentiment_label = "positive"
    elif avg_sentiment <= 35:
        sentiment_label = "very_negative"
    elif avg_sentiment <= 45:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"
    
    return {
        "score": round(avg_sentiment, 1),
        "sentiment": sentiment_label,
        "news_count": len(news_items),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "headlines": analyzed_headlines[:5],  # Top 5 for display
    }


def analyze_text_sentiment(text: str) -> float:
    """
    Analyze sentiment of a text string
    
    Returns score 0-100 (0=very negative, 50=neutral, 100=very positive)
    """
    text = text.lower()
    words = set(re.findall(r'\b\w+\b', text))
    
    # Count sentiment words
    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)
    very_positive = len(words & VERY_POSITIVE_WORDS)
    very_negative = len(words & VERY_NEGATIVE_WORDS)
    
    # Calculate score
    # Start at neutral (50), add/subtract based on word counts
    score = 50
    score += positive_count * 8
    score -= negative_count * 8
    score += very_positive * 15
    score -= very_negative * 15
    
    # Clamp to 0-100
    return max(0, min(100, score))


def get_sentiment_score(
    news_items: List[Dict[str, Any]],
    stock_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate overall sentiment score combining multiple factors
    
    Args:
        news_items: List of news items
        stock_info: Stock info dict (for price movement analysis)
    
    Returns:
        Dict with score and detailed breakdown
    """
    signals = []
    scores = []
    
    # 1. News Sentiment (60% weight)
    news_analysis = analyze_news_sentiment(news_items)
    news_score = news_analysis["score"]
    scores.append(("news", news_score, 0.60))
    
    if news_analysis["sentiment"] == "very_positive":
        signals.append(("news", "Very positive news sentiment"))
    elif news_analysis["sentiment"] == "positive":
        signals.append(("news", "Positive news sentiment"))
    elif news_analysis["sentiment"] == "very_negative":
        signals.append(("news", "Very negative news sentiment"))
    elif news_analysis["sentiment"] == "negative":
        signals.append(("news", "Negative news sentiment"))
    else:
        signals.append(("news", "Neutral news sentiment"))
    
    if news_analysis["news_count"] < 3:
        signals.append(("news", "Limited news coverage"))
    
    # 2. Price Movement Sentiment (25% weight)
    price_score = 50
    
    current = stock_info.get("current_price")
    prev_close = stock_info.get("previous_close")
    week_52_high = stock_info.get("52_week_high")
    week_52_low = stock_info.get("52_week_low")
    
    if current and prev_close:
        daily_change_pct = ((current - prev_close) / prev_close) * 100
        if daily_change_pct > 5:
            price_score += 25
            signals.append(("price", f"Strong daily gain (+{daily_change_pct:.1f}%)"))
        elif daily_change_pct > 2:
            price_score += 15
            signals.append(("price", f"Positive daily movement (+{daily_change_pct:.1f}%)"))
        elif daily_change_pct < -5:
            price_score -= 25
            signals.append(("price", f"Strong daily decline ({daily_change_pct:.1f}%)"))
        elif daily_change_pct < -2:
            price_score -= 15
            signals.append(("price", f"Negative daily movement ({daily_change_pct:.1f}%)"))
    
    # 52-week position
    if current and week_52_high and week_52_low:
        range_position = (current - week_52_low) / (week_52_high - week_52_low) if week_52_high > week_52_low else 0.5
        if range_position > 0.9:
            price_score += 10
            signals.append(("price", "Trading near 52-week high"))
        elif range_position < 0.2:
            price_score += 10  # Could be oversold opportunity
            signals.append(("price", "Trading near 52-week low - potential value"))
    
    price_score = max(0, min(100, price_score))
    scores.append(("price_action", price_score, 0.25))
    
    # 3. Volume Sentiment (15% weight)
    volume_score = 50
    
    avg_volume = stock_info.get("avg_volume")
    avg_volume_10d = stock_info.get("avg_volume_10d")
    
    if avg_volume and avg_volume_10d and avg_volume > 0:
        volume_change = ((avg_volume_10d - avg_volume) / avg_volume) * 100
        if volume_change > 50:
            volume_score += 20
            signals.append(("volume", f"Unusual volume increase (+{volume_change:.0f}%)"))
        elif volume_change > 20:
            volume_score += 10
            signals.append(("volume", f"Elevated volume (+{volume_change:.0f}%)"))
        elif volume_change < -30:
            volume_score -= 10
            signals.append(("volume", "Declining volume - reduced interest"))
    
    volume_score = max(0, min(100, volume_score))
    scores.append(("volume", volume_score, 0.15))
    
    # Calculate weighted final score
    final_score = sum(score * weight for _, score, weight in scores)
    
    return {
        "score": round(final_score, 1),
        "components": {name: score for name, score, _ in scores},
        "signals": signals,
        "news_analysis": news_analysis,
    }


def detect_unusual_activity(
    stock_info: Dict[str, Any],
    historical_data: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Detect unusual activity that might indicate significant moves
    
    Returns list of detected unusual activities
    """
    unusual = []
    
    # Volume spike
    avg_volume = stock_info.get("avg_volume")
    avg_volume_10d = stock_info.get("avg_volume_10d")
    
    if avg_volume and avg_volume_10d:
        if avg_volume_10d > avg_volume * 2:
            unusual.append({
                "type": "volume_spike",
                "description": f"Volume {avg_volume_10d/avg_volume:.1f}x above average",
                "significance": "high",
            })
    
    # Price gap
    current = stock_info.get("current_price")
    open_price = stock_info.get("open")
    prev_close = stock_info.get("previous_close")
    
    if open_price and prev_close:
        gap_pct = ((open_price - prev_close) / prev_close) * 100
        if abs(gap_pct) > 3:
            direction = "up" if gap_pct > 0 else "down"
            unusual.append({
                "type": "price_gap",
                "description": f"Gap {direction} {abs(gap_pct):.1f}% at open",
                "significance": "high" if abs(gap_pct) > 5 else "medium",
            })
    
    # Near 52-week high/low
    week_52_high = stock_info.get("52_week_high")
    week_52_low = stock_info.get("52_week_low")
    
    if current and week_52_high:
        if current >= week_52_high * 0.98:
            unusual.append({
                "type": "52_week_high",
                "description": "Trading at or near 52-week high",
                "significance": "medium",
            })
    
    if current and week_52_low:
        if current <= week_52_low * 1.02:
            unusual.append({
                "type": "52_week_low",
                "description": "Trading at or near 52-week low",
                "significance": "medium",
            })
    
    return unusual
