"""
Market data fetching from various sources
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging
import requests
from functools import lru_cache
import time

from app.config import get_settings, EXCHANGE_INFO

settings = get_settings()
logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    """Exception for market data errors"""
    pass


def get_yahoo_ticker(ticker: str, exchange: str) -> str:
    """Convert ticker to Yahoo Finance format"""
    # Handle special cases
    if exchange in EXCHANGE_INFO:
        suffix = EXCHANGE_INFO[exchange]["suffix"]
        if suffix and not ticker.endswith(suffix):
            return f"{ticker}{suffix}"
    
    # TSX Venture special handling
    if ".V" in ticker.upper() or exchange == "TSX-V":
        base = ticker.replace(".V", "").replace(".v", "")
        return f"{base}.V"
    
    # TSX handling
    if ".TO" in ticker.upper() or exchange == "TSX":
        base = ticker.replace(".TO", "").replace(".to", "")
        return f"{base}.TO"
    
    return ticker


def get_stock_info(ticker: str, exchange: str = "") -> Dict[str, Any]:
    """
    Get comprehensive stock information
    
    Returns dict with:
    - current_price
    - currency
    - market_cap
    - pe_ratio
    - forward_pe
    - peg_ratio
    - dividend_yield
    - 52_week_high
    - 52_week_low
    - avg_volume
    - beta
    - sector
    - industry
    - name
    """
    yahoo_ticker = get_yahoo_ticker(ticker, exchange)
    
    try:
        stock = yf.Ticker(yahoo_ticker)
        info = stock.info
        
        if not info or "regularMarketPrice" not in info:
            # Try fast_info for basic data
            fast = stock.fast_info
            return {
                "ticker": ticker,
                "yahoo_ticker": yahoo_ticker,
                "exchange": exchange,
                "current_price": getattr(fast, "last_price", None),
                "currency": getattr(fast, "currency", "USD"),
                "market_cap": getattr(fast, "market_cap", None),
                "name": ticker,
                "error": "Limited data available"
            }
        
        return {
            "ticker": ticker,
            "yahoo_ticker": yahoo_ticker,
            "exchange": exchange or info.get("exchange", ""),
            "current_price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "previous_close": info.get("previousClose"),
            "open": info.get("open"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "50_day_avg": info.get("fiftyDayAverage"),
            "200_day_avg": info.get("twoHundredDayAverage"),
            "avg_volume": info.get("averageVolume"),
            "avg_volume_10d": info.get("averageVolume10days"),
            "beta": info.get("beta"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "name": info.get("shortName") or info.get("longName") or ticker,
            "description": info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else "",
            "recommendation": info.get("recommendationMean"),
            "recommendation_key": info.get("recommendationKey"),
            "target_price": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "free_cash_flow": info.get("freeCashflow"),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
        }
        
    except Exception as e:
        logger.error(f"Error fetching stock info for {ticker}: {e}")
        raise MarketDataError(f"Failed to fetch data for {ticker}: {e}")


def get_historical_data(
    ticker: str, 
    exchange: str = "",
    period: str = "1y",
    interval: str = "1d"
) -> pd.DataFrame:
    """
    Get historical OHLCV data
    
    Args:
        ticker: Stock symbol
        exchange: Exchange name
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume, Adj Close
    """
    yahoo_ticker = get_yahoo_ticker(ticker, exchange)
    
    try:
        stock = yf.Ticker(yahoo_ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            raise MarketDataError(f"No historical data for {ticker}")
        
        # Ensure we have the required columns
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in df.columns:
                raise MarketDataError(f"Missing column {col} in data for {ticker}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {e}")
        raise MarketDataError(f"Failed to fetch historical data for {ticker}: {e}")


def get_multiple_quotes(tickers: List[Tuple[str, str]]) -> Dict[str, Dict[str, Any]]:
    """
    Get current quotes for multiple tickers efficiently
    
    Args:
        tickers: List of (ticker, exchange) tuples
    
    Returns:
        Dict mapping ticker to quote data
    """
    results = {}
    
    for ticker, exchange in tickers:
        try:
            yahoo_ticker = get_yahoo_ticker(ticker, exchange)
            stock = yf.Ticker(yahoo_ticker)
            fast = stock.fast_info
            
            results[ticker] = {
                "ticker": ticker,
                "exchange": exchange,
                "current_price": getattr(fast, "last_price", None),
                "previous_close": getattr(fast, "previous_close", None),
                "currency": getattr(fast, "currency", "USD"),
                "market_cap": getattr(fast, "market_cap", None),
            }
            
            # Calculate daily change
            if results[ticker]["current_price"] and results[ticker]["previous_close"]:
                change = results[ticker]["current_price"] - results[ticker]["previous_close"]
                change_pct = (change / results[ticker]["previous_close"]) * 100
                results[ticker]["daily_change"] = change
                results[ticker]["daily_change_pct"] = change_pct
            
        except Exception as e:
            logger.warning(f"Error fetching quote for {ticker}: {e}")
            results[ticker] = {
                "ticker": ticker,
                "exchange": exchange,
                "error": str(e)
            }
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    return results


def get_market_movers(region: str = "US", count: int = 20) -> Dict[str, List[Dict]]:
    """
    Get market movers (gainers, losers, most active)
    
    Note: This uses yfinance screeners which may have limited data
    """
    try:
        # Use yfinance screeners
        gainers = []
        losers = []
        most_active = []
        
        # For US market, we can use some popular screening
        if region == "US":
            # Get S&P 500 components and filter
            sp500 = yf.Ticker("^GSPC")
            # This is a simplified approach - in production you'd use a proper screener API
            
        return {
            "gainers": gainers[:count],
            "losers": losers[:count],
            "most_active": most_active[:count]
        }
        
    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        return {"gainers": [], "losers": [], "most_active": []}


def get_sector_performance() -> Dict[str, float]:
    """Get sector ETF performance for sector analysis"""
    sector_etfs = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financial": "XLF",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Materials": "XLB",
        "Industrial": "XLI",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communications": "XLC",
    }
    
    performance = {}
    
    for sector, etf in sector_etfs.items():
        try:
            stock = yf.Ticker(etf)
            fast = stock.fast_info
            current = getattr(fast, "last_price", None)
            prev = getattr(fast, "previous_close", None)
            
            if current and prev:
                performance[sector] = ((current - prev) / prev) * 100
        except Exception as e:
            logger.warning(f"Error fetching sector {sector}: {e}")
    
    return performance


def search_stocks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for stocks by name or ticker
    """
    try:
        # yfinance doesn't have a built-in search, so we use a workaround
        # In production, you'd use Finnhub or another API with search capability
        
        # Try direct lookup first
        results = []
        
        # Try the query as a ticker directly
        try:
            stock = yf.Ticker(query.upper())
            info = stock.info
            if info.get("regularMarketPrice"):
                results.append({
                    "ticker": query.upper(),
                    "name": info.get("shortName", query.upper()),
                    "exchange": info.get("exchange", ""),
                    "type": info.get("quoteType", "EQUITY"),
                })
        except:
            pass
        
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error searching stocks: {e}")
        return []


def is_market_open(exchange: str) -> bool:
    """Check if a market is currently open"""
    from datetime import datetime
    import pytz
    
    if exchange not in EXCHANGE_INFO:
        return True  # Assume open if unknown
    
    region = EXCHANGE_INFO[exchange]["region"]
    
    # Map region to market hours
    market_hours = {
        "US": {"open": 9, "close": 16, "tz": "America/New_York"},
        "CA": {"open": 9, "close": 16, "tz": "America/Toronto"},
        "EU": {"open": 8, "close": 17, "tz": "Europe/London"},
        "CH": {"open": 9, "close": 17, "tz": "Europe/Zurich"},
        "DE": {"open": 9, "close": 17, "tz": "Europe/Berlin"},
    }
    
    if region not in market_hours:
        return True
    
    hours = market_hours[region]
    tz = pytz.timezone(hours["tz"])
    now = datetime.now(tz)
    
    # Check if weekend
    if now.weekday() >= 5:
        return False
    
    # Check hours
    return hours["open"] <= now.hour < hours["close"]


def get_news_for_stock(ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent news for a stock using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            return []
        
        formatted_news = []
        for item in news[:limit]:
            formatted_news.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
                "published": datetime.fromtimestamp(item.get("providerPublishTime", 0)),
                "type": item.get("type", ""),
            })
        
        return formatted_news
        
    except Exception as e:
        logger.warning(f"Error fetching news for {ticker}: {e}")
        return []
