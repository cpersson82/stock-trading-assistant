"""
Scheduled jobs for market monitoring and analysis
"""
from datetime import datetime, time
from typing import List, Dict, Any
import logging
import pytz

from sqlalchemy.orm import Session

from app.database import get_db, Recommendation, RecommendationType, get_or_create_setting, update_setting
from app.analysis.engine import get_analysis_engine
from app.portfolio.manager import PortfolioManager
from app.notifications.email import get_email_sender
from app.data.screener import get_screening_candidates
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class MarketMonitor:
    """Monitors markets and generates recommendations"""
    
    def __init__(self):
        self.engine = get_analysis_engine()
        self.email_sender = get_email_sender()
        self.tz = pytz.timezone(settings.user_timezone)
    
    def is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours (no recommendations)"""
        now = datetime.now(self.tz)
        current_hour = now.hour
        
        start = settings.quiet_hours_start
        end = settings.quiet_hours_end
        
        if start > end:
            return current_hour >= start or current_hour < end
        else:
            return start <= current_hour < end
    
    def get_daily_recommendation_count(self, db: Session) -> int:
        """Get number of recommendations sent today"""
        today = datetime.now(self.tz).date()
        count = db.query(Recommendation).filter(
            Recommendation.created_at >= datetime.combine(today, time.min),
            Recommendation.email_sent == True
        ).count()
        return count
    
    def can_send_recommendation(self, db: Session) -> tuple:
        """Check if we can send a recommendation"""
        is_active = get_or_create_setting(db, "system_active", "true")
        if is_active.lower() != "true":
            return False, "System is paused"
        
        if self.is_quiet_hours():
            return False, "Quiet hours active"
        
        count = self.get_daily_recommendation_count(db)
        if count >= settings.max_daily_recommendations:
            return False, f"Daily limit reached ({settings.max_daily_recommendations})"
        
        return True, "OK"
    
    def run_market_check(self):
        """Main market check routine"""
        logger.info("Starting market check...")
        
        db = next(get_db())
        
        try:
            can_send, reason = self.can_send_recommendation(db)
            if not can_send:
                logger.info(f"Skipping recommendations: {reason}")
            
            portfolio_mgr = PortfolioManager(db)
            portfolio = portfolio_mgr.get_portfolio_value()
            
            # Analyze current holdings
            holdings_analysis = self._analyze_holdings(db, portfolio_mgr, portfolio)
            
            # Scan for new opportunities
            opportunities = self._scan_opportunities(db, portfolio_mgr, portfolio)
            
            # Record portfolio snapshot
            portfolio_mgr.record_snapshot()
            
            # Process recommendations
            self._process_recommendations(
                db, 
                holdings_analysis + opportunities,
                portfolio_mgr,
                portfolio,
                can_send
            )
            
            logger.info("Market check completed")
            
        except Exception as e:
            logger.error(f"Market check failed: {e}")
            raise
        finally:
            db.close()
    
    def _analyze_holdings(self, db: Session, portfolio_mgr: PortfolioManager, portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze current holdings for sell signals"""
        results = []
        
        for holding_data in portfolio.get("holdings", []):
            ticker = holding_data["ticker"]
            exchange = holding_data["exchange"]
            
            logger.info(f"Analyzing holding: {ticker}")
            
            analysis = self.engine.analyze_stock(ticker, exchange)
            
            if "error" in analysis:
                logger.warning(f"Analysis error for {ticker}: {analysis['error']}")
                continue
            
            action = self.engine.get_action_details(
                analysis,
                portfolio["total_value_chf"],
                portfolio["cash_chf"],
                holding_data["shares"]
            )
            
            results.append({
                "type": "holding",
                "ticker": ticker,
                "exchange": exchange,
                "analysis": analysis,
                "action": action,
                "current_shares": holding_data["shares"],
            })
        
        return results
    
    def _scan_opportunities(self, db: Session, portfolio_mgr: PortfolioManager, portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan watchlist for buy opportunities"""
        results = []
        
        candidates = get_screening_candidates()
        current_tickers = {h["ticker"] for h in portfolio.get("holdings", [])}
        candidates = [(t, e) for t, e in candidates if t not in current_tickers]
        candidates = candidates[:20]
        
        for ticker, exchange in candidates:
            logger.info(f"Scanning opportunity: {ticker}")
            
            analysis = self.engine.analyze_stock(ticker, exchange)
            
            if "error" in analysis:
                continue
            
            if analysis.get("combined_score", 0) < 60:
                continue
            
            action = self.engine.get_action_details(
                analysis,
                portfolio["total_value_chf"],
                portfolio["cash_chf"],
                0
            )
            
            if action.get("action") in ["BUY", "STRONG_BUY"]:
                results.append({
                    "type": "opportunity",
                    "ticker": ticker,
                    "exchange": exchange,
                    "analysis": analysis,
                    "action": action,
                    "current_shares": 0,
                })
        
        return results
    
    def _process_recommendations(self, db: Session, analyses: List[Dict[str, Any]], portfolio_mgr: PortfolioManager, portfolio: Dict[str, Any], can_send: bool):
        """Process analyses and send recommendations"""
        
        def priority_key(item):
            rec = item["analysis"].get("recommendation", "HOLD")
            score = item["analysis"].get("combined_score", 50)
            
            if rec in ["STRONG_SELL", "SELL"]:
                return (0, -score)
            elif rec == "STRONG_BUY":
                return (1, -score)
            elif rec == "BUY":
                return (2, -score)
            else:
                return (3, -score)
        
        analyses.sort(key=priority_key)
        
        sent_count = 0
        for item in analyses:
            analysis = item["analysis"]
            action = item["action"]
            
            rec_type = analysis.get("recommendation", "HOLD")
            
            if rec_type == "HOLD" and not analysis.get("unusual_activity"):
                continue
            
            if not can_send or sent_count >= settings.max_daily_recommendations:
                logger.info(f"Would recommend {rec_type} for {item['ticker']} (score: {analysis.get('combined_score')})")
                continue
            
            recommendation = self._create_recommendation(db, item, portfolio, portfolio_mgr)
            
            if self._send_recommendation_email(recommendation, analysis, action, portfolio):
                recommendation.email_sent = True
                db.commit()
                sent_count += 1
                logger.info(f"Sent {rec_type} recommendation for {item['ticker']}")
    
    def _create_recommendation(self, db: Session, item: Dict[str, Any], portfolio: Dict[str, Any], portfolio_mgr: PortfolioManager) -> Recommendation:
        """Create a recommendation record in database"""
        analysis = item["analysis"]
        action = item["action"]
        
        rec = Recommendation(
            ticker=item["ticker"],
            exchange=item["exchange"],
            recommendation_type=RecommendationType(analysis["recommendation"]),
            price_at_recommendation=analysis["current_price"],
            price_currency=analysis["currency"],
            price_in_chf=analysis["price_chf"],
            recommended_shares=abs(action.get("shares", 0)) if action.get("shares") else None,
            recommended_value_chf=action.get("value_chf"),
            stop_loss_price=action.get("stop_loss"),
            technical_score=analysis["technical"]["score"],
            fundamental_score=analysis["fundamental"]["score"],
            sentiment_score=analysis["sentiment"]["score"],
            combined_score=analysis["combined_score"],
            reasoning=analysis["reasoning"],
            portfolio_value_before=portfolio["total_value_chf"],
            cash_after_trade=self._calculate_cash_after(portfolio, action),
        )
        
        db.add(rec)
        db.commit()
        db.refresh(rec)
        
        return rec
    
    def _calculate_cash_after(self, portfolio: Dict[str, Any], action: Dict[str, Any]) -> float:
        """Calculate cash after trade"""
        cash = portfolio["cash_chf"]
        value = action.get("value_chf", 0)
        shares = action.get("shares", 0)
        
        if shares > 0:
            return cash - value
        elif shares < 0:
            return cash + value
        return cash
    
    def _send_recommendation_email(self, recommendation: Recommendation, analysis: Dict[str, Any], action: Dict[str, Any], portfolio: Dict[str, Any]) -> bool:
        """Send recommendation email"""
        return self.email_sender.send_recommendation(
            ticker=recommendation.ticker,
            exchange=recommendation.exchange,
            recommendation=recommendation.recommendation_type.value,
            current_price=recommendation.price_at_recommendation,
            currency=recommendation.price_currency,
            price_chf=recommendation.price_in_chf,
            recommended_shares=action.get("shares"),
            position_value_chf=action.get("value_chf"),
            stop_loss=action.get("stop_loss"),
            reasoning=recommendation.reasoning,
            portfolio_impact={
                "cash_after": recommendation.cash_after_trade or portfolio["cash_chf"],
                "total_portfolio": portfolio["total_value_chf"],
            },
            analysis_scores={
                "technical": recommendation.technical_score,
                "fundamental": recommendation.fundamental_score,
                "sentiment": recommendation.sentiment_score,
                "combined": recommendation.combined_score,
            }
        )
    
    def analyze_single_stock(self, ticker: str, exchange: str = "") -> Dict[str, Any]:
        """Analyze a single stock (for manual requests)"""
        db = next(get_db())
        
        try:
            portfolio_mgr = PortfolioManager(db)
            portfolio = portfolio_mgr.get_portfolio_value()
            
            holding = portfolio_mgr.get_holding(ticker)
            current_shares = holding.shares if holding else 0
            
            analysis = self.engine.analyze_stock(ticker, exchange)
            
            if "error" not in analysis:
                action = self.engine.get_action_details(
                    analysis,
                    portfolio["total_value_chf"],
                    portfolio["cash_chf"],
                    current_shares
                )
                analysis["action"] = action
            
            return analysis
            
        finally:
            db.close()


_monitor = None

def get_market_monitor() -> MarketMonitor:
    """Get or create market monitor singleton"""
    global _monitor
    if _monitor is None:
        _monitor = MarketMonitor()
    return _monitor


def run_scheduled_check():
    """Entry point for scheduled market checks"""
    monitor = get_market_monitor()
    monitor.run_market_check()
