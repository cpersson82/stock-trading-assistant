"""
Fundamental analysis module
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_fundamental_score(stock_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate fundamental score (0-100) based on financial metrics
    
    Args:
        stock_info: Dict from market_data.get_stock_info()
    
    Returns:
        Dict with score and detailed breakdown
    """
    signals = []
    scores = []
    
    # 1. Valuation Score (30% weight)
    valuation_score = 50
    valuation_signals = []
    
    # P/E Ratio
    pe_ratio = stock_info.get("pe_ratio")
    forward_pe = stock_info.get("forward_pe")
    
    if pe_ratio is not None:
        if pe_ratio < 0:
            valuation_score -= 15
            valuation_signals.append(f"Negative P/E ({pe_ratio:.1f}) - company unprofitable")
        elif pe_ratio < 15:
            valuation_score += 15
            valuation_signals.append(f"Low P/E ({pe_ratio:.1f}) - potentially undervalued")
        elif pe_ratio < 25:
            valuation_score += 5
            valuation_signals.append(f"Moderate P/E ({pe_ratio:.1f}) - fair valuation")
        elif pe_ratio < 40:
            valuation_score -= 5
            valuation_signals.append(f"High P/E ({pe_ratio:.1f}) - growth expectations priced in")
        else:
            valuation_score -= 15
            valuation_signals.append(f"Very high P/E ({pe_ratio:.1f}) - potentially overvalued")
    
    # Forward P/E vs Trailing P/E (earnings growth expectation)
    if pe_ratio is not None and forward_pe is not None and pe_ratio > 0 and forward_pe > 0:
        if forward_pe < pe_ratio * 0.85:
            valuation_score += 10
            valuation_signals.append("Forward P/E significantly lower - strong earnings growth expected")
        elif forward_pe > pe_ratio * 1.15:
            valuation_score -= 10
            valuation_signals.append("Forward P/E higher - earnings decline expected")
    
    # PEG Ratio
    peg_ratio = stock_info.get("peg_ratio")
    if peg_ratio is not None and peg_ratio > 0:
        if peg_ratio < 1:
            valuation_score += 10
            valuation_signals.append(f"PEG ratio below 1 ({peg_ratio:.2f}) - undervalued relative to growth")
        elif peg_ratio > 2:
            valuation_score -= 10
            valuation_signals.append(f"PEG ratio above 2 ({peg_ratio:.2f}) - expensive relative to growth")
    
    # Price to Book
    price_to_book = stock_info.get("price_to_book")
    if price_to_book is not None:
        if price_to_book < 1:
            valuation_score += 10
            valuation_signals.append(f"P/B below 1 ({price_to_book:.2f}) - trading below book value")
        elif price_to_book > 10:
            valuation_score -= 5
            valuation_signals.append(f"High P/B ({price_to_book:.2f}) - premium valuation")
    
    valuation_score = max(0, min(100, valuation_score))
    scores.append(("valuation", valuation_score, 0.30))
    signals.extend([("valuation", s) for s in valuation_signals])
    
    # 2. Growth Score (25% weight)
    growth_score = 50
    growth_signals = []
    
    # Earnings Growth
    earnings_growth = stock_info.get("earnings_growth")
    if earnings_growth is not None:
        eg_pct = earnings_growth * 100
        if eg_pct > 25:
            growth_score += 20
            growth_signals.append(f"Strong earnings growth ({eg_pct:.1f}%)")
        elif eg_pct > 10:
            growth_score += 10
            growth_signals.append(f"Solid earnings growth ({eg_pct:.1f}%)")
        elif eg_pct > 0:
            growth_score += 5
            growth_signals.append(f"Positive earnings growth ({eg_pct:.1f}%)")
        elif eg_pct > -10:
            growth_score -= 5
            growth_signals.append(f"Slight earnings decline ({eg_pct:.1f}%)")
        else:
            growth_score -= 15
            growth_signals.append(f"Significant earnings decline ({eg_pct:.1f}%)")
    
    # Revenue Growth
    revenue_growth = stock_info.get("revenue_growth")
    if revenue_growth is not None:
        rg_pct = revenue_growth * 100
        if rg_pct > 20:
            growth_score += 15
            growth_signals.append(f"Strong revenue growth ({rg_pct:.1f}%)")
        elif rg_pct > 10:
            growth_score += 10
            growth_signals.append(f"Solid revenue growth ({rg_pct:.1f}%)")
        elif rg_pct > 0:
            growth_score += 5
            growth_signals.append(f"Positive revenue growth ({rg_pct:.1f}%)")
        else:
            growth_score -= 10
            growth_signals.append(f"Revenue decline ({rg_pct:.1f}%)")
    
    growth_score = max(0, min(100, growth_score))
    scores.append(("growth", growth_score, 0.25))
    signals.extend([("growth", s) for s in growth_signals])
    
    # 3. Profitability Score (20% weight)
    profitability_score = 50
    profitability_signals = []
    
    # Profit Margin
    profit_margin = stock_info.get("profit_margin")
    if profit_margin is not None:
        pm_pct = profit_margin * 100
        if pm_pct > 20:
            profitability_score += 15
            profitability_signals.append(f"High profit margin ({pm_pct:.1f}%)")
        elif pm_pct > 10:
            profitability_score += 10
            profitability_signals.append(f"Solid profit margin ({pm_pct:.1f}%)")
        elif pm_pct > 0:
            profitability_score += 5
            profitability_signals.append(f"Positive profit margin ({pm_pct:.1f}%)")
        else:
            profitability_score -= 15
            profitability_signals.append(f"Negative profit margin ({pm_pct:.1f}%)")
    
    # Operating Margin
    operating_margin = stock_info.get("operating_margin")
    if operating_margin is not None:
        om_pct = operating_margin * 100
        if om_pct > 25:
            profitability_score += 10
            profitability_signals.append(f"Excellent operating margin ({om_pct:.1f}%)")
        elif om_pct > 15:
            profitability_score += 5
            profitability_signals.append(f"Good operating margin ({om_pct:.1f}%)")
        elif om_pct < 0:
            profitability_score -= 10
            profitability_signals.append(f"Negative operating margin ({om_pct:.1f}%)")
    
    # Free Cash Flow
    free_cash_flow = stock_info.get("free_cash_flow")
    if free_cash_flow is not None:
        if free_cash_flow > 0:
            profitability_score += 10
            profitability_signals.append("Positive free cash flow")
        else:
            profitability_score -= 10
            profitability_signals.append("Negative free cash flow")
    
    profitability_score = max(0, min(100, profitability_score))
    scores.append(("profitability", profitability_score, 0.20))
    signals.extend([("profitability", s) for s in profitability_signals])
    
    # 4. Financial Health Score (15% weight)
    health_score = 50
    health_signals = []
    
    # Debt to Equity
    debt_to_equity = stock_info.get("debt_to_equity")
    if debt_to_equity is not None:
        if debt_to_equity < 30:
            health_score += 15
            health_signals.append(f"Low debt-to-equity ({debt_to_equity:.1f}%) - strong balance sheet")
        elif debt_to_equity < 100:
            health_score += 5
            health_signals.append(f"Moderate debt-to-equity ({debt_to_equity:.1f}%)")
        elif debt_to_equity < 200:
            health_score -= 5
            health_signals.append(f"High debt-to-equity ({debt_to_equity:.1f}%)")
        else:
            health_score -= 15
            health_signals.append(f"Very high debt ({debt_to_equity:.1f}%) - leverage risk")
    
    # Current Ratio
    current_ratio = stock_info.get("current_ratio")
    if current_ratio is not None:
        if current_ratio > 2:
            health_score += 10
            health_signals.append(f"Strong current ratio ({current_ratio:.2f}) - good liquidity")
        elif current_ratio > 1:
            health_score += 5
            health_signals.append(f"Adequate current ratio ({current_ratio:.2f})")
        else:
            health_score -= 15
            health_signals.append(f"Low current ratio ({current_ratio:.2f}) - liquidity concern")
    
    # Total Cash vs Debt
    total_cash = stock_info.get("total_cash")
    total_debt = stock_info.get("total_debt")
    if total_cash is not None and total_debt is not None and total_debt > 0:
        cash_debt_ratio = total_cash / total_debt
        if cash_debt_ratio > 1:
            health_score += 10
            health_signals.append("Cash exceeds total debt - strong position")
        elif cash_debt_ratio > 0.5:
            health_score += 5
            health_signals.append("Adequate cash relative to debt")
    
    health_score = max(0, min(100, health_score))
    scores.append(("financial_health", health_score, 0.15))
    signals.extend([("financial_health", s) for s in health_signals])
    
    # 5. Analyst Sentiment Score (10% weight)
    analyst_score = 50
    analyst_signals = []
    
    # Analyst Recommendation (1-5 scale: 1=strong buy, 5=strong sell)
    recommendation = stock_info.get("recommendation")
    recommendation_key = stock_info.get("recommendation_key")
    
    if recommendation is not None:
        if recommendation < 2:
            analyst_score += 25
            analyst_signals.append(f"Strong analyst buy rating ({recommendation:.2f})")
        elif recommendation < 2.5:
            analyst_score += 15
            analyst_signals.append(f"Analyst buy rating ({recommendation:.2f})")
        elif recommendation < 3.5:
            analyst_score += 0
            analyst_signals.append(f"Analyst hold rating ({recommendation:.2f})")
        elif recommendation < 4.5:
            analyst_score -= 15
            analyst_signals.append(f"Analyst sell rating ({recommendation:.2f})")
        else:
            analyst_score -= 25
            analyst_signals.append(f"Strong analyst sell rating ({recommendation:.2f})")
    
    # Price Target vs Current
    target_price = stock_info.get("target_price")
    current_price = stock_info.get("current_price")
    
    if target_price is not None and current_price is not None and current_price > 0:
        upside = ((target_price - current_price) / current_price) * 100
        if upside > 30:
            analyst_score += 15
            analyst_signals.append(f"Significant upside to target ({upside:.1f}%)")
        elif upside > 10:
            analyst_score += 10
            analyst_signals.append(f"Positive upside to target ({upside:.1f}%)")
        elif upside > -10:
            analyst_signals.append(f"Near analyst target ({upside:.1f}%)")
        else:
            analyst_score -= 15
            analyst_signals.append(f"Trading above target ({upside:.1f}%)")
    
    analyst_score = max(0, min(100, analyst_score))
    scores.append(("analyst_sentiment", analyst_score, 0.10))
    signals.extend([("analyst_sentiment", s) for s in analyst_signals])
    
    # Calculate weighted final score
    final_score = sum(score * weight for _, score, weight in scores)
    
    return {
        "score": round(final_score, 1),
        "components": {name: score for name, score, _ in scores},
        "signals": signals,
        "key_metrics": {
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "peg_ratio": peg_ratio,
            "profit_margin": profit_margin,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "earnings_growth": earnings_growth,
            "revenue_growth": revenue_growth,
        }
    }


def classify_stock_risk(stock_info: Dict[str, Any]) -> str:
    """
    Classify a stock's risk level based on fundamentals
    
    Returns: 'conservative', 'moderate', or 'aggressive'
    """
    market_cap = stock_info.get("market_cap")
    beta = stock_info.get("beta")
    sector = stock_info.get("sector", "").lower()
    exchange = stock_info.get("exchange", "")
    
    # Junior exchanges are aggressive
    if "venture" in exchange.lower() or "-v" in exchange.lower():
        return "aggressive"
    
    # Very small caps are aggressive
    if market_cap is not None:
        if market_cap < 300_000_000:  # Under $300M
            return "aggressive"
        elif market_cap < 2_000_000_000:  # Under $2B
            return "moderate"
    
    # High beta stocks are aggressive
    if beta is not None:
        if beta > 1.5:
            return "aggressive"
        elif beta > 1.1:
            return "moderate"
    
    # Certain sectors are typically more volatile
    aggressive_sectors = ["technology", "biotechnology", "cryptocurrency", "cannabis"]
    conservative_sectors = ["utilities", "consumer defensive", "healthcare"]
    
    for s in aggressive_sectors:
        if s in sector:
            return "aggressive" if market_cap and market_cap < 10_000_000_000 else "moderate"
    
    for s in conservative_sectors:
        if s in sector:
            return "conservative"
    
    # Default to moderate
    return "moderate"


def get_sector_comparison(stock_info: Dict[str, Any], sector_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Compare stock metrics to sector averages
    
    Note: sector_data would come from an external source in production
    """
    # Simplified sector averages (in production, fetch from API)
    sector_averages = {
        "Technology": {"pe": 30, "profit_margin": 0.15, "debt_to_equity": 50},
        "Healthcare": {"pe": 25, "profit_margin": 0.12, "debt_to_equity": 60},
        "Financial": {"pe": 12, "profit_margin": 0.20, "debt_to_equity": 150},
        "Consumer Cyclical": {"pe": 20, "profit_margin": 0.08, "debt_to_equity": 80},
        "Basic Materials": {"pe": 15, "profit_margin": 0.10, "debt_to_equity": 40},
        "Energy": {"pe": 12, "profit_margin": 0.08, "debt_to_equity": 50},
        "default": {"pe": 20, "profit_margin": 0.10, "debt_to_equity": 70},
    }
    
    sector = stock_info.get("sector", "default")
    averages = sector_averages.get(sector, sector_averages["default"])
    
    comparisons = {}
    
    pe_ratio = stock_info.get("pe_ratio")
    if pe_ratio is not None and pe_ratio > 0:
        comparisons["pe_vs_sector"] = {
            "stock": pe_ratio,
            "sector_avg": averages["pe"],
            "difference_pct": ((pe_ratio - averages["pe"]) / averages["pe"]) * 100
        }
    
    profit_margin = stock_info.get("profit_margin")
    if profit_margin is not None:
        comparisons["margin_vs_sector"] = {
            "stock": profit_margin,
            "sector_avg": averages["profit_margin"],
            "difference_pct": ((profit_margin - averages["profit_margin"]) / averages["profit_margin"]) * 100 if averages["profit_margin"] else 0
        }
    
    debt_to_equity = stock_info.get("debt_to_equity")
    if debt_to_equity is not None:
        comparisons["debt_vs_sector"] = {
            "stock": debt_to_equity,
            "sector_avg": averages["debt_to_equity"],
            "difference_pct": ((debt_to_equity - averages["debt_to_equity"]) / averages["debt_to_equity"]) * 100 if averages["debt_to_equity"] else 0
        }
    
    return comparisons
