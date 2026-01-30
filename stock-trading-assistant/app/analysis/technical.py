"""
Technical analysis module
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators on OHLCV data
    
    Args:
        df: DataFrame with Open, High, Low, Close, Volume columns
    
    Returns:
        DataFrame with added indicator columns
    """
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    
    # Moving Averages
    df["SMA_5"] = close.rolling(window=5).mean()
    df["SMA_10"] = close.rolling(window=10).mean()
    df["SMA_20"] = close.rolling(window=20).mean()
    df["SMA_50"] = close.rolling(window=50).mean()
    df["SMA_200"] = close.rolling(window=200).mean()
    
    # Exponential Moving Averages
    df["EMA_9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    df["EMA_26"] = close.ewm(span=26, adjust=False).mean()
    
    # MACD
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Histogram"] = df["MACD"] - df["MACD_Signal"]
    
    # RSI
    df["RSI"] = calculate_rsi(close, period=14)
    
    # Stochastic RSI
    df["StochRSI"] = calculate_stoch_rsi(close, period=14)
    
    # Bollinger Bands
    df["BB_Middle"] = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df["BB_Upper"] = df["BB_Middle"] + (bb_std * 2)
    df["BB_Lower"] = df["BB_Middle"] - (bb_std * 2)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]
    df["BB_Position"] = (close - df["BB_Lower"]) / (df["BB_Upper"] - df["BB_Lower"])
    
    # ATR (Average True Range)
    df["ATR"] = calculate_atr(high, low, close, period=14)
    
    # ADX (Average Directional Index)
    df["ADX"], df["DI_Plus"], df["DI_Minus"] = calculate_adx(high, low, close, period=14)
    
    # Volume indicators
    df["Volume_SMA"] = volume.rolling(window=20).mean()
    df["Volume_Ratio"] = volume / df["Volume_SMA"]
    
    # OBV (On Balance Volume)
    df["OBV"] = calculate_obv(close, volume)
    
    # Money Flow Index
    df["MFI"] = calculate_mfi(high, low, close, volume, period=14)
    
    # Price Rate of Change
    df["ROC_5"] = (close - close.shift(5)) / close.shift(5) * 100
    df["ROC_10"] = (close - close.shift(10)) / close.shift(10) * 100
    df["ROC_20"] = (close - close.shift(20)) / close.shift(20) * 100
    
    # Williams %R
    df["Williams_R"] = calculate_williams_r(high, low, close, period=14)
    
    # CCI (Commodity Channel Index)
    df["CCI"] = calculate_cci(high, low, close, period=20)
    
    return df


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_stoch_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Stochastic RSI"""
    rsi = calculate_rsi(close, period)
    stoch_rsi = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min())
    return stoch_rsi * 100


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Average Directional Index"""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    atr = calculate_atr(high, low, close, period)
    
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx, plus_di, minus_di


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On Balance Volume"""
    obv = (np.sign(close.diff()) * volume).cumsum()
    return obv


def calculate_mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Money Flow Index"""
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume
    
    money_flow_diff = typical_price.diff()
    
    positive_flow = raw_money_flow.where(money_flow_diff > 0, 0).rolling(period).sum()
    negative_flow = raw_money_flow.where(money_flow_diff < 0, 0).rolling(period).sum()
    
    money_ratio = positive_flow / negative_flow
    mfi = 100 - (100 / (1 + money_ratio))
    
    return mfi


def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Williams %R"""
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
    return williams_r


def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Calculate Commodity Channel Index"""
    typical_price = (high + low + close) / 3
    sma = typical_price.rolling(period).mean()
    mad = typical_price.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
    
    cci = (typical_price - sma) / (0.015 * mad)
    return cci


def get_technical_score(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate overall technical score (0-100) based on indicators
    
    Returns:
        Dict with score and detailed breakdown
    """
    if df.empty or len(df) < 50:
        return {"score": 50, "signals": [], "error": "Insufficient data"}
    
    latest = df.iloc[-1]
    signals = []
    scores = []
    
    # 1. Trend Score (25% weight)
    trend_score = 50
    trend_signals = []
    
    # Price vs Moving Averages
    close = latest["Close"]
    
    if pd.notna(latest.get("SMA_20")):
        if close > latest["SMA_20"]:
            trend_score += 5
            trend_signals.append("Price above SMA20 (bullish)")
        else:
            trend_score -= 5
            trend_signals.append("Price below SMA20 (bearish)")
    
    if pd.notna(latest.get("SMA_50")):
        if close > latest["SMA_50"]:
            trend_score += 5
            trend_signals.append("Price above SMA50 (bullish)")
        else:
            trend_score -= 5
            trend_signals.append("Price below SMA50 (bearish)")
    
    if pd.notna(latest.get("SMA_200")):
        if close > latest["SMA_200"]:
            trend_score += 10
            trend_signals.append("Price above SMA200 (long-term bullish)")
        else:
            trend_score -= 10
            trend_signals.append("Price below SMA200 (long-term bearish)")
    
    # Golden/Death Cross
    if pd.notna(latest.get("SMA_50")) and pd.notna(latest.get("SMA_200")):
        if latest["SMA_50"] > latest["SMA_200"]:
            trend_score += 10
            trend_signals.append("Golden cross active (SMA50 > SMA200)")
        else:
            trend_score -= 10
            trend_signals.append("Death cross active (SMA50 < SMA200)")
    
    trend_score = max(0, min(100, trend_score))
    scores.append(("trend", trend_score, 0.25))
    signals.extend([("trend", s) for s in trend_signals])
    
    # 2. Momentum Score (25% weight)
    momentum_score = 50
    momentum_signals = []
    
    # RSI
    if pd.notna(latest.get("RSI")):
        rsi = latest["RSI"]
        if rsi < 30:
            momentum_score += 15
            momentum_signals.append(f"RSI oversold ({rsi:.1f}) - potential bounce")
        elif rsi > 70:
            momentum_score -= 15
            momentum_signals.append(f"RSI overbought ({rsi:.1f}) - potential pullback")
        elif 40 <= rsi <= 60:
            momentum_score += 5
            momentum_signals.append(f"RSI neutral ({rsi:.1f})")
    
    # MACD
    if pd.notna(latest.get("MACD")) and pd.notna(latest.get("MACD_Signal")):
        if latest["MACD"] > latest["MACD_Signal"]:
            momentum_score += 10
            momentum_signals.append("MACD bullish crossover")
        else:
            momentum_score -= 10
            momentum_signals.append("MACD bearish crossover")
        
        # MACD histogram trend
        if pd.notna(latest.get("MACD_Histogram")):
            hist_now = latest["MACD_Histogram"]
            hist_prev = df["MACD_Histogram"].iloc[-2] if len(df) > 1 else hist_now
            if hist_now > hist_prev:
                momentum_score += 5
                momentum_signals.append("MACD histogram increasing")
    
    # Stochastic RSI
    if pd.notna(latest.get("StochRSI")):
        stoch = latest["StochRSI"]
        if stoch < 20:
            momentum_score += 10
            momentum_signals.append(f"Stochastic RSI oversold ({stoch:.1f})")
        elif stoch > 80:
            momentum_score -= 10
            momentum_signals.append(f"Stochastic RSI overbought ({stoch:.1f})")
    
    momentum_score = max(0, min(100, momentum_score))
    scores.append(("momentum", momentum_score, 0.25))
    signals.extend([("momentum", s) for s in momentum_signals])
    
    # 3. Volatility Score (20% weight)
    volatility_score = 50
    volatility_signals = []
    
    # Bollinger Band position
    if pd.notna(latest.get("BB_Position")):
        bb_pos = latest["BB_Position"]
        if bb_pos < 0.2:
            volatility_score += 15
            volatility_signals.append("Price near lower Bollinger Band (potential support)")
        elif bb_pos > 0.8:
            volatility_score -= 10
            volatility_signals.append("Price near upper Bollinger Band (potential resistance)")
        
        # Bollinger squeeze
        if pd.notna(latest.get("BB_Width")):
            # Compare to recent average
            recent_width = df["BB_Width"].tail(20).mean()
            if latest["BB_Width"] < recent_width * 0.7:
                volatility_score += 10
                volatility_signals.append("Bollinger squeeze detected - breakout likely")
    
    # ADX
    if pd.notna(latest.get("ADX")):
        adx = latest["ADX"]
        if adx > 25:
            volatility_signals.append(f"Strong trend (ADX: {adx:.1f})")
            # Trend direction
            if pd.notna(latest.get("DI_Plus")) and pd.notna(latest.get("DI_Minus")):
                if latest["DI_Plus"] > latest["DI_Minus"]:
                    volatility_score += 10
                    volatility_signals.append("Bullish trend confirmed (DI+ > DI-)")
                else:
                    volatility_score -= 10
                    volatility_signals.append("Bearish trend confirmed (DI- > DI+)")
        else:
            volatility_signals.append(f"Weak trend (ADX: {adx:.1f})")
    
    volatility_score = max(0, min(100, volatility_score))
    scores.append(("volatility", volatility_score, 0.20))
    signals.extend([("volatility", s) for s in volatility_signals])
    
    # 4. Volume Score (15% weight)
    volume_score = 50
    volume_signals = []
    
    if pd.notna(latest.get("Volume_Ratio")):
        vol_ratio = latest["Volume_Ratio"]
        if vol_ratio > 1.5:
            volume_score += 15
            volume_signals.append(f"High volume ({vol_ratio:.1f}x average) - confirms move")
        elif vol_ratio < 0.5:
            volume_score -= 10
            volume_signals.append(f"Low volume ({vol_ratio:.1f}x average) - weak conviction")
    
    # MFI
    if pd.notna(latest.get("MFI")):
        mfi = latest["MFI"]
        if mfi < 20:
            volume_score += 10
            volume_signals.append(f"MFI oversold ({mfi:.1f}) - buying pressure likely")
        elif mfi > 80:
            volume_score -= 10
            volume_signals.append(f"MFI overbought ({mfi:.1f}) - selling pressure likely")
    
    volume_score = max(0, min(100, volume_score))
    scores.append(("volume", volume_score, 0.15))
    signals.extend([("volume", s) for s in volume_signals])
    
    # 5. Price Action Score (15% weight)
    price_action_score = 50
    price_action_signals = []
    
    # Rate of change
    if pd.notna(latest.get("ROC_5")):
        roc5 = latest["ROC_5"]
        if roc5 > 5:
            price_action_score += 10
            price_action_signals.append(f"Strong 5-day momentum (+{roc5:.1f}%)")
        elif roc5 < -5:
            price_action_score -= 10
            price_action_signals.append(f"Weak 5-day momentum ({roc5:.1f}%)")
    
    # Williams %R
    if pd.notna(latest.get("Williams_R")):
        williams = latest["Williams_R"]
        if williams < -80:
            price_action_score += 10
            price_action_signals.append(f"Williams %R oversold ({williams:.1f})")
        elif williams > -20:
            price_action_score -= 10
            price_action_signals.append(f"Williams %R overbought ({williams:.1f})")
    
    # CCI
    if pd.notna(latest.get("CCI")):
        cci = latest["CCI"]
        if cci < -100:
            price_action_score += 10
            price_action_signals.append(f"CCI oversold ({cci:.1f})")
        elif cci > 100:
            price_action_score -= 10
            price_action_signals.append(f"CCI overbought ({cci:.1f})")
    
    price_action_score = max(0, min(100, price_action_score))
    scores.append(("price_action", price_action_score, 0.15))
    signals.extend([("price_action", s) for s in price_action_signals])
    
    # Calculate weighted final score
    final_score = sum(score * weight for _, score, weight in scores)
    
    return {
        "score": round(final_score, 1),
        "components": {name: score for name, score, _ in scores},
        "signals": signals,
        "latest_indicators": {
            "RSI": latest.get("RSI"),
            "MACD": latest.get("MACD"),
            "MACD_Signal": latest.get("MACD_Signal"),
            "BB_Position": latest.get("BB_Position"),
            "ADX": latest.get("ADX"),
            "Volume_Ratio": latest.get("Volume_Ratio"),
        }
    }


def detect_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect chart patterns in price data
    
    Returns dict with detected patterns and their significance
    """
    if len(df) < 50:
        return {"patterns": [], "error": "Insufficient data for pattern detection"}
    
    patterns = []
    
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    
    # Look for double bottom (bullish reversal)
    if _detect_double_bottom(low[-30:]):
        patterns.append({
            "name": "Double Bottom",
            "type": "bullish_reversal",
            "significance": "high",
            "description": "Potential bullish reversal pattern forming"
        })
    
    # Look for double top (bearish reversal)
    if _detect_double_top(high[-30:]):
        patterns.append({
            "name": "Double Top",
            "type": "bearish_reversal",
            "significance": "high",
            "description": "Potential bearish reversal pattern forming"
        })
    
    # Look for higher highs and higher lows (uptrend)
    if _is_uptrend(high[-20:], low[-20:]):
        patterns.append({
            "name": "Uptrend",
            "type": "bullish_continuation",
            "significance": "medium",
            "description": "Higher highs and higher lows indicate uptrend"
        })
    
    # Look for lower highs and lower lows (downtrend)
    if _is_downtrend(high[-20:], low[-20:]):
        patterns.append({
            "name": "Downtrend",
            "type": "bearish_continuation",
            "significance": "medium",
            "description": "Lower highs and lower lows indicate downtrend"
        })
    
    return {"patterns": patterns}


def _detect_double_bottom(lows: np.ndarray, tolerance: float = 0.03) -> bool:
    """Detect double bottom pattern"""
    if len(lows) < 10:
        return False
    
    # Find local minima
    minima_idx = []
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            minima_idx.append(i)
    
    # Check for two similar lows
    for i in range(len(minima_idx) - 1):
        for j in range(i + 1, len(minima_idx)):
            if abs(minima_idx[j] - minima_idx[i]) >= 5:  # At least 5 bars apart
                low1 = lows[minima_idx[i]]
                low2 = lows[minima_idx[j]]
                if abs(low1 - low2) / low1 <= tolerance:
                    return True
    
    return False


def _detect_double_top(highs: np.ndarray, tolerance: float = 0.03) -> bool:
    """Detect double top pattern"""
    if len(highs) < 10:
        return False
    
    # Find local maxima
    maxima_idx = []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            maxima_idx.append(i)
    
    # Check for two similar highs
    for i in range(len(maxima_idx) - 1):
        for j in range(i + 1, len(maxima_idx)):
            if abs(maxima_idx[j] - maxima_idx[i]) >= 5:
                high1 = highs[maxima_idx[i]]
                high2 = highs[maxima_idx[j]]
                if abs(high1 - high2) / high1 <= tolerance:
                    return True
    
    return False


def _is_uptrend(highs: np.ndarray, lows: np.ndarray) -> bool:
    """Check if price is in an uptrend"""
    if len(highs) < 10:
        return False
    
    # Compare first half to second half
    mid = len(highs) // 2
    first_avg_high = np.mean(highs[:mid])
    second_avg_high = np.mean(highs[mid:])
    first_avg_low = np.mean(lows[:mid])
    second_avg_low = np.mean(lows[mid:])
    
    return second_avg_high > first_avg_high and second_avg_low > first_avg_low


def _is_downtrend(highs: np.ndarray, lows: np.ndarray) -> bool:
    """Check if price is in a downtrend"""
    if len(highs) < 10:
        return False
    
    mid = len(highs) // 2
    first_avg_high = np.mean(highs[:mid])
    second_avg_high = np.mean(highs[mid:])
    first_avg_low = np.mean(lows[:mid])
    second_avg_low = np.mean(lows[mid:])
    
    return second_avg_high < first_avg_high and second_avg_low < first_avg_low
