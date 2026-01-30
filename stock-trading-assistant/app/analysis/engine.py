"""
Main analysis engine that combines technical, fundamental, and sentiment analysis
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging

from app.analysis.technical import calculate_technical_indicators, get_technical_score, detect_patterns
from app.analysis.fundamental import get_fundamental_score, classify_stock_risk
from app.analysis.sentiment import get_sentiment_score, detect_unusual_activity
from app.data.market_data import get_stock_info, get_historical_data, get_news_for_stock
from app.data.forex import convert_to_chf
from app.config import get_settings, ANALYSIS_THRESHOLDS

settings = get_settings()
logger = logging.getLogger(__name__)


class AnalysisEngine:
    """
    Main analysis engine for stock evaluation
    """
    
    def __init__(self):
        self.thresholds = ANALYSIS_THRESHOLDS
        
        # Default weights (can be adjusted based on market conditions)
        self.weights = {
            "technical": 0.40,
            "fundamental": 0.35,
            "sentiment": 0.15,
            "risk_adjusted": 0.10,
        }
    
    def analyze_stock(
        self, 
        ticker: str, 
        exchange: str = "",
        include_news: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on a stock
        
        Args:
            ticker: Stock symbol
            exchange: Exchange name
            include_news: Whether to fetch and analyze news
        
        Returns:
            Complete analysis dict with scores and recommendations
        """
        try:
            # Fetch all required data
            stock_info = get_stock_info(ticker, exchange)
            
            if not stock_info.get("current_price"):
                return {
                    "error": f"Could not fetch data for {ticker}",
                    "ticker": ticker,
                    "exchange": exchange,
                }
            
            # Get historical data for technical analysis
            try:
                historical = get_historical_data(ticker, exchange, period="1y")
            except Exception as e:
                logger.warning(f"Could not fetch historical data for {ticker}: {e}")
                historical = None
            
            # Get news for sentiment
            news_items = []
            if include_news:
                try:
                    news_items = get_news_for_stock(ticker)
                except Exception as e:
                    logger.warning(f"Could not fetch news for {ticker}: {e}")
            
            # Perform analysis
            analysis = self._perform_analysis(stock_info, historical, news_items)
            
            # Add metadata
            analysis["ticker"] = ticker
            analysis["exchange"] = exchange or stock_info.get("exchange", "")
            analysis["name"] = stock_info.get("name", ticker)
            analysis["current_price"] = stock_info.get("current_price")
            analysis["currency"] = stock_info.get("currency", "USD")
            analysis["price_chf"] = convert_to_chf(
                stock_info.get("current_price", 0),
                stock_info.get("currency", "USD")
            )
            analysis["analyzed_at"] = datetime.utcnow().isoformat()
            analysis["stock_info"] = stock_info
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return {
                "error": str(e),
                "ticker": ticker,
                "exchange": exchange,
            }
    
    def _perform_analysis(
        self,
        stock_info: Dict[str, Any],
        historical: Optional[Any],
        news_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform all analysis components
        """
        # Technical Analysis
        technical_result = {"score": 50, "signals": [], "error": "No historical data"}
        patterns_result = {"patterns": []}
        
        if historical is not None and not historical.empty:
            # Calculate indicators
            df_with_indicators = calculate_technical_indicators(historical)
            technical_result = get_technical_score(df_with_indicators)
            patterns_result = detect_patterns(historical)
        
        # Fundamental Analysis
        fundamental_result = get_fundamental_score(stock_info)
        
        # Sentiment Analysis
        sentiment_result = get_sentiment_score(news_items, stock_info)
        
        # Unusual Activity Detection
        unusual_activity = detect_unusual_activity(stock_info, historical)
        
        # Risk Classification
        risk_category = classify_stock_risk(stock_info)
        
        # Calculate Risk-Adjusted Score
        risk_adjusted_score = self._calculate_risk_adjusted_score(
            technical_result["score"],
            fundamental_result["score"],
            sentiment_result["score"],
            risk_category,
            unusual_activity
        )
        
        # Calculate Combined Score
        combined_score = self._calculate_combined_score(
            technical_result["score"],
            fundamental_result["score"],
            sentiment_result["score"],
            risk_adjusted_score
        )
        
        # Generate Recommendation
        recommendation = self._generate_recommendation(
            combined_score,
            technical_result,
            fundamental_result,
            sentiment_result,
            risk_category
        )
        
        # Generate Reasoning
        reasoning = self._generate_reasoning(
            technical_result,
            fundamental_result,
            sentiment_result,
            patterns_result,
            unusual_activity,
            recommendation
        )
        
        return {
            "combined_score": combined_score,
            "recommendation": recommendation,
            "reasoning": reasoning,
            "technical": technical_result,
            "fundamental": fundamental_result,
            "sentiment": sentiment_result,
            "patterns": patterns_result,
            "unusual_activity": unusual_activity,
            "risk_category": risk_category,
            "risk_adjusted_score": risk_adjusted_score,
        }
    
    def _calculate_risk_adjusted_score(
        self,
        technical_score: float,
        fundamental_score: float,
        sentiment_score: float,
        risk_category: str,
        unusual_activity: List[Dict]
    ) -> float:
        """
        Calculate risk-adjusted score
        """
        # Base score is average of other scores
        base_score = (technical_score + fundamental_score + sentiment_score) / 3
        
        # Adjust based on risk category
        risk_adjustments = {
            "conservative": 10,   # Bonus for low-risk stocks
            "moderate": 0,
            "aggressive": -10,    # Penalty for high-risk stocks
        }
        
        score = base_score + risk_adjustments.get(risk_category, 0)
        
        # Unusual activity can be a signal (positive or negative)
        for activity in unusual_activity:
            if activity["type"] == "volume_spike":
                # High volume could confirm a move (slight positive)
                score += 5
            elif activity["type"] == "52_week_high":
                # Near highs might mean momentum but also risk
                score -= 5
            elif activity["type"] == "52_week_low":
                # Near lows could be opportunity or value trap
                score += 0  # Neutral
        
        return max(0, min(100, score))
    
    def _calculate_combined_score(
        self,
        technical_score: float,
        fundamental_score: float,
        sentiment_score: float,
        risk_adjusted_score: float
    ) -> float:
        """
        Calculate weighted combined score
        """
        combined = (
            technical_score * self.weights["technical"] +
            fundamental_score * self.weights["fundamental"] +
            sentiment_score * self.weights["sentiment"] +
            risk_adjusted_score * self.weights["risk_adjusted"]
        )
        
        return round(combined, 1)
    
    def _generate_recommendation(
        self,
        combined_score: float,
        technical: Dict,
        fundamental: Dict,
        sentiment: Dict,
        risk_category: str
    ) -> str:
        """
        Generate recommendation based on combined analysis
        """
        if combined_score >= self.thresholds["strong_buy"]:
            return "STRONG_BUY"
        elif combined_score >= self.thresholds["buy"]:
            return "BUY"
        elif combined_score <= self.thresholds["strong_sell"]:
            return "STRONG_SELL"
        elif combined_score <= self.thresholds["sell"]:
            return "SELL"
        else:
            return "HOLD"
    
    def _generate_reasoning(
        self,
        technical: Dict,
        fundamental: Dict,
        sentiment: Dict,
        patterns: Dict,
        unusual_activity: List[Dict],
        recommendation: str
    ) -> str:
        """
        Generate human-readable reasoning for the recommendation
        """
        reasons = []
        
        # Technical reasoning
        tech_score = technical.get("score", 50)
        if tech_score >= 65:
            reasons.append("Technical indicators are bullish")
        elif tech_score <= 35:
            reasons.append("Technical indicators are bearish")
        
        # Add key technical signals
        tech_signals = technical.get("signals", [])
        important_signals = [s[1] for s in tech_signals if "bullish" in s[1].lower() or "bearish" in s[1].lower()][:2]
        reasons.extend(important_signals)
        
        # Fundamental reasoning
        fund_score = fundamental.get("score", 50)
        if fund_score >= 65:
            reasons.append("Fundamentals are strong")
        elif fund_score <= 35:
            reasons.append("Fundamentals show weakness")
        
        # Add key fundamental points
        fund_signals = fundamental.get("signals", [])
        for category, signal in fund_signals[:2]:
            if "growth" in signal.lower() or "margin" in signal.lower():
                reasons.append(signal)
                break
        
        # Sentiment reasoning
        sent_score = sentiment.get("score", 50)
        if sent_score >= 60:
            reasons.append("Market sentiment is positive")
        elif sent_score <= 40:
            reasons.append("Market sentiment is negative")
        
        # Patterns
        detected_patterns = patterns.get("patterns", [])
        for pattern in detected_patterns[:1]:
            reasons.append(f"{pattern['name']} pattern detected")
        
        # Unusual activity
        for activity in unusual_activity[:1]:
            reasons.append(activity["description"])
        
        # Combine into readable text
        if not reasons:
            return f"Analysis suggests {recommendation.lower().replace('_', ' ')} based on neutral indicators across technical, fundamental, and sentiment analysis."
        
        return ". ".join(reasons[:4]) + "."
    
    def get_action_details(
        self,
        analysis: Dict[str, Any],
        portfolio_value_chf: float,
        cash_available_chf: float,
        current_position_shares: float = 0
    ) -> Dict[str, Any]:
        """
        Get specific action details (shares to buy/sell, position size)
        
        Args:
            analysis: Analysis result from analyze_stock
            portfolio_value_chf: Total portfolio value in CHF
            cash_available_chf: Available cash in CHF
            current_position_shares: Current shares held (0 if none)
        
        Returns:
            Dict with action details
        """
        recommendation = analysis.get("recommendation", "HOLD")
        risk_category = analysis.get("risk_category", "moderate")
        price_chf = analysis.get("price_chf", 0)
        current_price = analysis.get("current_price", 0)
        currency = analysis.get("currency", "USD")
        
        if price_chf <= 0:
            return {
                "action": "HOLD",
                "shares": 0,
                "reason": "Invalid price data"
            }
        
        # Position sizing based on risk category
        max_position_pct = {
            "conservative": 0.25,
            "moderate": 0.15,
            "aggressive": 0.10,
        }.get(risk_category, 0.15)
        
        max_position_value_chf = portfolio_value_chf * max_position_pct
        
        # Calculate current position value
        current_position_value_chf = current_position_shares * price_chf
        
        if recommendation in ["STRONG_BUY", "BUY"]:
            # Calculate how many shares to buy
            if current_position_value_chf >= max_position_value_chf:
                return {
                    "action": "HOLD",
                    "shares": 0,
                    "reason": f"Already at maximum position size ({max_position_pct*100:.0f}% of portfolio)"
                }
            
            available_to_invest = min(
                cash_available_chf,
                max_position_value_chf - current_position_value_chf
            )
            
            if available_to_invest < price_chf:
                return {
                    "action": "HOLD",
                    "shares": 0,
                    "reason": "Insufficient cash for minimum position",
                    "cash_needed_chf": price_chf - cash_available_chf if cash_available_chf < price_chf else 0
                }
            
            shares_to_buy = int(available_to_invest / price_chf)
            
            if shares_to_buy > 0:
                # Calculate stop loss
                stop_loss_pct = {
                    "conservative": 0.08,
                    "moderate": 0.12,
                    "aggressive": 0.18,
                }.get(risk_category, 0.12)
                
                stop_loss_price = current_price * (1 - stop_loss_pct)
                
                return {
                    "action": recommendation,
                    "shares": shares_to_buy,
                    "value_chf": shares_to_buy * price_chf,
                    "price": current_price,
                    "price_chf": price_chf,
                    "currency": currency,
                    "stop_loss": round(stop_loss_price, 2),
                    "stop_loss_pct": stop_loss_pct * 100,
                    "max_position_value_chf": max_position_value_chf,
                }
        
        elif recommendation in ["STRONG_SELL", "SELL"]:
            if current_position_shares <= 0:
                return {
                    "action": "HOLD",
                    "shares": 0,
                    "reason": "No position to sell"
                }
            
            # For STRONG_SELL, recommend selling entire position
            # For SELL, recommend selling half
            if recommendation == "STRONG_SELL":
                shares_to_sell = current_position_shares
            else:
                shares_to_sell = int(current_position_shares / 2)
            
            return {
                "action": recommendation,
                "shares": -shares_to_sell,  # Negative indicates sell
                "value_chf": shares_to_sell * price_chf,
                "price": current_price,
                "price_chf": price_chf,
                "currency": currency,
            }
        
        else:  # HOLD
            return {
                "action": "HOLD",
                "shares": 0,
                "current_position_shares": current_position_shares,
                "current_position_value_chf": current_position_value_chf,
            }
    
    def adjust_weights_for_market_conditions(self, volatility_index: float = None):
        """
        Adjust analysis weights based on market conditions
        
        Args:
            volatility_index: VIX or similar (if available)
        """
        if volatility_index is not None:
            if volatility_index > 30:
                # High volatility - weight technical more
                self.weights = {
                    "technical": 0.50,
                    "fundamental": 0.25,
                    "sentiment": 0.15,
                    "risk_adjusted": 0.10,
                }
            elif volatility_index < 15:
                # Low volatility - weight fundamentals more
                self.weights = {
                    "technical": 0.30,
                    "fundamental": 0.45,
                    "sentiment": 0.15,
                    "risk_adjusted": 0.10,
                }
            else:
                # Normal conditions - use default weights
                self.weights = {
                    "technical": 0.40,
                    "fundamental": 0.35,
                    "sentiment": 0.15,
                    "risk_adjusted": 0.10,
                }


# Singleton instance
_engine = None

def get_analysis_engine() -> AnalysisEngine:
    """Get or create the analysis engine singleton"""
    global _engine
    if _engine is None:
        _engine = AnalysisEngine()
    return _engine
