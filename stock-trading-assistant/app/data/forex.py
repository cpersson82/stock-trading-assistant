"""
Currency conversion and forex rates
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from functools import lru_cache
import logging
import yfinance as yf

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Cache for exchange rates (refreshed every hour)
_rates_cache: Dict[str, tuple] = {}  # {currency: (rate_to_chf, timestamp)}
CACHE_DURATION = timedelta(hours=1)


def get_exchange_rate_to_chf(from_currency: str) -> float:
    """
    Get exchange rate from a currency to CHF
    
    Args:
        from_currency: Source currency code (USD, EUR, CAD, GBP, etc.)
    
    Returns:
        Exchange rate (multiply by this to convert to CHF)
    """
    from_currency = from_currency.upper()
    
    if from_currency == "CHF":
        return 1.0
    
    # Check cache
    if from_currency in _rates_cache:
        rate, timestamp = _rates_cache[from_currency]
        if datetime.now() - timestamp < CACHE_DURATION:
            return rate
    
    # Try yfinance first (most reliable)
    rate = _get_rate_yfinance(from_currency)
    
    if rate is None:
        # Fallback to ECB API
        rate = _get_rate_ecb(from_currency)
    
    if rate is None:
        # Use hardcoded approximate rates as last resort
        rate = _get_fallback_rate(from_currency)
        logger.warning(f"Using fallback rate for {from_currency}/CHF: {rate}")
    
    # Cache the rate
    _rates_cache[from_currency] = (rate, datetime.now())
    
    return rate


def _get_rate_yfinance(from_currency: str) -> Optional[float]:
    """Get exchange rate using yfinance"""
    try:
        # yfinance uses format like "USDCHF=X"
        ticker = f"{from_currency}CHF=X"
        fx = yf.Ticker(ticker)
        
        # Try fast_info first
        fast = fx.fast_info
        rate = getattr(fast, "last_price", None)
        
        if rate:
            return float(rate)
        
        # Try historical data
        hist = fx.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        
        return None
        
    except Exception as e:
        logger.debug(f"yfinance rate fetch failed for {from_currency}: {e}")
        return None


def _get_rate_ecb(from_currency: str) -> Optional[float]:
    """Get exchange rate from ECB API"""
    try:
        # ECB provides rates against EUR, so we need to convert
        url = "https://api.frankfurter.app/latest"
        params = {"from": from_currency, "to": "CHF"}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("rates", {}).get("CHF")
        
    except Exception as e:
        logger.debug(f"ECB rate fetch failed for {from_currency}: {e}")
        return None


def _get_fallback_rate(from_currency: str) -> float:
    """Fallback exchange rates (approximate)"""
    # These are approximate rates as of early 2024
    # Update periodically if API fetching consistently fails
    fallback_rates = {
        "USD": 0.88,   # 1 USD = 0.88 CHF
        "EUR": 0.95,   # 1 EUR = 0.95 CHF
        "GBP": 1.10,   # 1 GBP = 1.10 CHF
        "CAD": 0.65,   # 1 CAD = 0.65 CHF
        "JPY": 0.0059, # 1 JPY = 0.0059 CHF
        "AUD": 0.57,   # 1 AUD = 0.57 CHF
        "HKD": 0.11,   # 1 HKD = 0.11 CHF
        "SGD": 0.66,   # 1 SGD = 0.66 CHF
        "SEK": 0.084,  # 1 SEK = 0.084 CHF
        "NOK": 0.082,  # 1 NOK = 0.082 CHF
        "DKK": 0.127,  # 1 DKK = 0.127 CHF
    }
    
    return fallback_rates.get(from_currency, 1.0)


def convert_to_chf(amount: float, from_currency: str) -> float:
    """
    Convert an amount to CHF
    
    Args:
        amount: Amount in source currency
        from_currency: Source currency code
    
    Returns:
        Amount in CHF
    """
    rate = get_exchange_rate_to_chf(from_currency)
    return amount * rate


def convert_from_chf(amount_chf: float, to_currency: str) -> float:
    """
    Convert an amount from CHF to another currency
    
    Args:
        amount_chf: Amount in CHF
        to_currency: Target currency code
    
    Returns:
        Amount in target currency
    """
    rate = get_exchange_rate_to_chf(to_currency)
    if rate == 0:
        return 0
    return amount_chf / rate


def get_all_rates() -> Dict[str, float]:
    """Get all common exchange rates to CHF"""
    currencies = ["USD", "EUR", "GBP", "CAD", "JPY", "AUD", "HKD", "SGD"]
    rates = {}
    
    for currency in currencies:
        try:
            rates[currency] = get_exchange_rate_to_chf(currency)
        except Exception as e:
            logger.error(f"Error getting rate for {currency}: {e}")
    
    rates["CHF"] = 1.0
    return rates


def get_currency_trend(currency_pair: str, days: int = 30) -> Dict[str, any]:
    """
    Get currency trend data
    
    Args:
        currency_pair: e.g., "USDCHF"
        days: Number of days of history
    
    Returns:
        Dict with trend info
    """
    try:
        ticker = f"{currency_pair}=X"
        fx = yf.Ticker(ticker)
        hist = fx.history(period=f"{days}d")
        
        if hist.empty:
            return {"error": "No data available"}
        
        current = float(hist["Close"].iloc[-1])
        start = float(hist["Close"].iloc[0])
        
        change = current - start
        change_pct = (change / start) * 100
        
        # Simple trend analysis
        sma_short = hist["Close"].tail(5).mean()
        sma_long = hist["Close"].tail(20).mean()
        
        trend = "neutral"
        if sma_short > sma_long * 1.01:
            trend = "strengthening"
        elif sma_short < sma_long * 0.99:
            trend = "weakening"
        
        return {
            "current_rate": current,
            "start_rate": start,
            "change": change,
            "change_pct": change_pct,
            "trend": trend,
            "high": float(hist["High"].max()),
            "low": float(hist["Low"].min()),
        }
        
    except Exception as e:
        logger.error(f"Error getting currency trend for {currency_pair}: {e}")
        return {"error": str(e)}
