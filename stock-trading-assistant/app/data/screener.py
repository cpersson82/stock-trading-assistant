"""
Stock screening and discovery module
"""
import yfinance as yf
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import time

from app.config import get_settings, EXCHANGE_INFO

settings = get_settings()
logger = logging.getLogger(__name__)


# Predefined watchlists for different categories
WATCHLIST_CATEGORIES = {
    "swiss_blue_chips": [
        ("NESN", "SIX"),   # Nestle
        ("NOVN", "SIX"),   # Novartis
        ("ROG", "SIX"),    # Roche
        ("UBSG", "SIX"),   # UBS
        ("ABBN", "SIX"),   # ABB
        ("ZURN", "SIX"),   # Zurich Insurance
        ("SREN", "SIX"),   # Swiss Re
        ("GIVN", "SIX"),   # Givaudan
        ("LONN", "SIX"),   # Lonza
    ],
    "us_large_cap": [
        ("AAPL", "NASDAQ"),
        ("MSFT", "NASDAQ"),
        ("GOOGL", "NASDAQ"),
        ("AMZN", "NASDAQ"),
        ("NVDA", "NASDAQ"),
        ("META", "NASDAQ"),
        ("TSLA", "NASDAQ"),
        ("BRK-B", "NYSE"),
        ("JPM", "NYSE"),
        ("V", "NYSE"),
    ],
    "us_growth": [
        ("AMD", "NASDAQ"),
        ("CRM", "NYSE"),
        ("SNOW", "NYSE"),
        ("PLTR", "NYSE"),
        ("NET", "NYSE"),
        ("DDOG", "NASDAQ"),
        ("CRWD", "NASDAQ"),
        ("ZS", "NASDAQ"),
    ],
    "canadian_mining": [
        ("ABX", "TSX"),    # Barrick Gold
        ("NEM", "NYSE"),   # Newmont
        ("TECK-B", "TSX"), # Teck Resources
        ("FM", "TSX"),     # First Quantum
        ("LUN", "TSX"),    # Lundin Mining
        ("ERO", "TSX"),    # Ero Copper
        ("CS", "TSX"),     # Capstone Copper
    ],
    "canadian_junior_mining": [
        ("ITR", "TSX-V"),  # Integra Resources (user's holding)
        ("NOVR", "TSX-V"), # Nova Royalty
        ("SBB", "TSX-V"),  # Sabina Gold
        ("MAG", "TSX"),    # MAG Silver
    ],
    "etfs_diversified": [
        ("SPY", "NYSE"),   # S&P 500
        ("QQQ", "NASDAQ"), # Nasdaq 100
        ("VTI", "NYSE"),   # Total Market
        ("VEA", "NYSE"),   # Developed Markets
        ("VWO", "NYSE"),   # Emerging Markets
        ("GLD", "NYSE"),   # Gold
        ("SLV", "NYSE"),   # Silver
    ],
    "etfs_sector": [
        ("XLK", "NYSE"),   # Technology
        ("XLF", "NYSE"),   # Financials
        ("XLE", "NYSE"),   # Energy
        ("XLV", "NYSE"),   # Healthcare
        ("XLI", "NYSE"),   # Industrials
        ("XLRE", "NYSE"),  # Real Estate
    ],
    "european_stocks": [
        ("ASML", "NASDAQ"), # ASML (also traded on AMS)
        ("SAP", "NYSE"),    # SAP
        ("NVO", "NYSE"),    # Novo Nordisk
        ("TTE", "NYSE"),    # TotalEnergies
        ("SAN", "NYSE"),    # Santander
    ],
}


def get_screening_candidates(
    categories: Optional[List[str]] = None,
    include_user_holdings: bool = True
) -> List[tuple]:
    """
    Get list of stocks to screen
    
    Args:
        categories: List of category names to include (None = all)
        include_user_holdings: Whether to include user's current holdings
    
    Returns:
        List of (ticker, exchange) tuples
    """
    candidates = []
    
    # Add from categories
    if categories is None:
        categories = list(WATCHLIST_CATEGORIES.keys())
    
    for category in categories:
        if category in WATCHLIST_CATEGORIES:
            candidates.extend(WATCHLIST_CATEGORIES[category])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for ticker, exchange in candidates:
        if ticker not in seen:
            seen.add(ticker)
            unique_candidates.append((ticker, exchange))
    
    return unique_candidates


def screen_for_momentum(candidates: List[tuple], min_volume: int = 100000) -> List[Dict[str, Any]]:
    """
    Screen stocks for momentum signals
    
    Returns stocks with:
    - Price above 20-day SMA
    - Recent volume spike
    - Positive momentum
    """
    results = []
    
    for ticker, exchange in candidates:
        try:
            yahoo_ticker = _get_yahoo_ticker(ticker, exchange)
            stock = yf.Ticker(yahoo_ticker)
            hist = stock.history(period="3mo")
            
            if hist.empty or len(hist) < 20:
                continue
            
            current_price = hist["Close"].iloc[-1]
            sma_20 = hist["Close"].tail(20).mean()
            avg_volume = hist["Volume"].tail(20).mean()
            current_volume = hist["Volume"].iloc[-1]
            
            # Check criteria
            if current_price > sma_20 and avg_volume >= min_volume:
                # Calculate momentum
                price_5d_ago = hist["Close"].iloc[-5] if len(hist) >= 5 else current_price
                momentum_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
                
                price_20d_ago = hist["Close"].iloc[-20] if len(hist) >= 20 else current_price
                momentum_20d = ((current_price - price_20d_ago) / price_20d_ago) * 100
                
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                results.append({
                    "ticker": ticker,
                    "exchange": exchange,
                    "current_price": current_price,
                    "sma_20": sma_20,
                    "price_vs_sma": ((current_price - sma_20) / sma_20) * 100,
                    "momentum_5d": momentum_5d,
                    "momentum_20d": momentum_20d,
                    "volume_ratio": volume_ratio,
                    "avg_volume": avg_volume,
                })
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            logger.debug(f"Error screening {ticker}: {e}")
            continue
    
    # Sort by momentum
    results.sort(key=lambda x: x.get("momentum_5d", 0), reverse=True)
    return results


def screen_for_value(candidates: List[tuple]) -> List[Dict[str, Any]]:
    """
    Screen stocks for value signals
    
    Returns stocks with:
    - Low P/E relative to sector
    - Strong fundamentals
    - Price near 52-week low
    """
    results = []
    
    for ticker, exchange in candidates:
        try:
            yahoo_ticker = _get_yahoo_ticker(ticker, exchange)
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info
            
            if not info:
                continue
            
            pe_ratio = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            price_to_book = info.get("priceToBook")
            current_price = info.get("regularMarketPrice")
            week_52_low = info.get("fiftyTwoWeekLow")
            week_52_high = info.get("fiftyTwoWeekHigh")
            
            # Skip if missing key data
            if not all([current_price, week_52_low, week_52_high]):
                continue
            
            # Calculate metrics
            price_vs_52w_range = (current_price - week_52_low) / (week_52_high - week_52_low) if week_52_high > week_52_low else 0.5
            
            # Value criteria: lower half of 52-week range, reasonable P/E
            if price_vs_52w_range < 0.5 and (pe_ratio is None or pe_ratio < 25):
                results.append({
                    "ticker": ticker,
                    "exchange": exchange,
                    "current_price": current_price,
                    "pe_ratio": pe_ratio,
                    "forward_pe": forward_pe,
                    "price_to_book": price_to_book,
                    "52w_low": week_52_low,
                    "52w_high": week_52_high,
                    "price_vs_52w_range": price_vs_52w_range,
                    "sector": info.get("sector", "Unknown"),
                })
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            logger.debug(f"Error screening {ticker}: {e}")
            continue
    
    # Sort by proximity to 52-week low
    results.sort(key=lambda x: x.get("price_vs_52w_range", 1))
    return results


def screen_for_volatility_breakout(candidates: List[tuple]) -> List[Dict[str, Any]]:
    """
    Screen for stocks breaking out of low volatility
    
    Returns stocks with:
    - Bollinger Band squeeze (low volatility)
    - Recent price movement suggesting breakout
    """
    results = []
    
    for ticker, exchange in candidates:
        try:
            yahoo_ticker = _get_yahoo_ticker(ticker, exchange)
            stock = yf.Ticker(yahoo_ticker)
            hist = stock.history(period="3mo")
            
            if hist.empty or len(hist) < 20:
                continue
            
            close = hist["Close"]
            current_price = close.iloc[-1]
            
            # Calculate Bollinger Bands
            sma_20 = close.tail(20).mean()
            std_20 = close.tail(20).std()
            upper_band = sma_20 + (2 * std_20)
            lower_band = sma_20 - (2 * std_20)
            
            # Band width (squeeze indicator)
            band_width = (upper_band - lower_band) / sma_20
            
            # Historical band width for comparison
            hist_band_widths = []
            for i in range(20, len(close)):
                period_close = close.iloc[i-20:i]
                period_sma = period_close.mean()
                period_std = period_close.std()
                width = (2 * period_std * 2) / period_sma
                hist_band_widths.append(width)
            
            if not hist_band_widths:
                continue
            
            avg_band_width = sum(hist_band_widths) / len(hist_band_widths)
            
            # Look for squeeze (current width much lower than average)
            if band_width < avg_band_width * 0.7:
                # Check if breaking out
                if current_price > upper_band or current_price < lower_band:
                    breakout_direction = "bullish" if current_price > upper_band else "bearish"
                else:
                    breakout_direction = "squeeze"
                
                results.append({
                    "ticker": ticker,
                    "exchange": exchange,
                    "current_price": current_price,
                    "sma_20": sma_20,
                    "upper_band": upper_band,
                    "lower_band": lower_band,
                    "band_width": band_width,
                    "avg_band_width": avg_band_width,
                    "squeeze_ratio": band_width / avg_band_width,
                    "breakout_direction": breakout_direction,
                })
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            logger.debug(f"Error screening {ticker}: {e}")
            continue
    
    # Sort by squeeze intensity
    results.sort(key=lambda x: x.get("squeeze_ratio", 1))
    return results


def _get_yahoo_ticker(ticker: str, exchange: str) -> str:
    """Convert ticker to Yahoo Finance format"""
    if exchange in EXCHANGE_INFO:
        suffix = EXCHANGE_INFO[exchange]["suffix"]
        if suffix and not ticker.endswith(suffix):
            return f"{ticker}{suffix}"
    
    if ".V" in ticker.upper() or exchange == "TSX-V":
        base = ticker.replace(".V", "").replace(".v", "")
        return f"{base}.V"
    
    if ".TO" in ticker.upper() or exchange == "TSX":
        base = ticker.replace(".TO", "").replace(".to", "")
        return f"{base}.TO"
    
    return ticker


def discover_opportunities(
    categories: Optional[List[str]] = None,
    max_results: int = 10
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run all screens and return top opportunities
    
    Returns:
        Dict with 'momentum', 'value', 'breakout' keys
    """
    candidates = get_screening_candidates(categories)
    
    return {
        "momentum": screen_for_momentum(candidates)[:max_results],
        "value": screen_for_value(candidates)[:max_results],
        "breakout": screen_for_volatility_breakout(candidates)[:max_results],
    }
