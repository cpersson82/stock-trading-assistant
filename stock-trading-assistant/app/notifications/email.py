"""
Email notification module for sending trading recommendations
"""
import resend
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailSender:
    """Sends email notifications for trading recommendations"""
    
    def __init__(self):
        self.recipient = settings.email_recipient
        self.api_key = settings.resend_api_key
        if self.api_key:
            resend.api_key = self.api_key
    
    def is_configured(self) -> bool:
        """Check if email is properly configured"""
        return bool(self.api_key and self.recipient)
    
    def send_recommendation(
        self,
        ticker: str,
        exchange: str,
        recommendation: str,
        current_price: float,
        currency: str,
        price_chf: float,
        recommended_shares: Optional[float],
        position_value_chf: Optional[float],
        stop_loss: Optional[float],
        reasoning: str,
        portfolio_impact: Dict[str, float],
        analysis_scores: Dict[str, float]
    ) -> bool:
        """Send a trading recommendation email"""
        if not self.is_configured():
            logger.warning("Email not configured, skipping notification")
            return False
        
        try:
            action_info = {
                "STRONG_BUY": ("🟢", "Strong Buy"),
                "BUY": ("🟢", "Buy"),
                "HOLD": ("🟡", "Hold"),
                "SELL": ("🔴", "Sell"),
                "STRONG_SELL": ("🔴", "Strong Sell"),
            }
            emoji, action_text = action_info.get(recommendation, ("⚪", recommendation))
            
            subject = f"{emoji} [{action_text}] {ticker} - Trading Recommendation"
            
            html_content = self._create_html_content(
                ticker, exchange, recommendation, current_price, currency,
                price_chf, recommended_shares, position_value_chf, stop_loss,
                reasoning, portfolio_impact, analysis_scores
            )
            
            params = {
                "from": "Trading Assistant <onboarding@resend.dev>",
                "to": [self.recipient],
                "subject": subject,
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Recommendation email sent for {ticker}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _create_html_content(
        self,
        ticker: str,
        exchange: str,
        recommendation: str,
        current_price: float,
        currency: str,
        price_chf: float,
        recommended_shares: Optional[float],
        position_value_chf: Optional[float],
        stop_loss: Optional[float],
        reasoning: str,
        portfolio_impact: Dict[str, float],
        analysis_scores: Dict[str, float]
    ) -> str:
        """Create HTML email content"""
        
        colors = {
            "STRONG_BUY": "#16a34a",
            "BUY": "#22c55e",
            "HOLD": "#eab308",
            "SELL": "#f97316",
            "STRONG_SELL": "#dc2626",
        }
        color = colors.get(recommendation, "#6b7280")
        
        action_line = ""
        if recommendation in ["STRONG_BUY", "BUY"] and recommended_shares:
            action_line = f"<strong>Buy {int(recommended_shares)} shares</strong>"
        elif recommendation in ["STRONG_SELL", "SELL"] and recommended_shares:
            action_line = f"<strong>Sell {abs(int(recommended_shares))} shares</strong>"
        else:
            action_line = "<strong>Hold position</strong>"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header .ticker {{ font-size: 32px; font-weight: bold; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
        .price-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .price {{ font-size: 28px; font-weight: bold; color: #111827; }}
        .section {{ margin: 20px 0; }}
        .section-title {{ font-weight: bold; color: #374151; margin-bottom: 8px; border-bottom: 2px solid {color}; padding-bottom: 4px; }}
        .scores {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .score-item {{ background: white; padding: 10px 15px; border-radius: 6px; flex: 1; min-width: 100px; text-align: center; }}
        .score-value {{ font-size: 20px; font-weight: bold; color: {color}; }}
        .score-label {{ font-size: 12px; color: #6b7280; }}
        .reasoning {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {color}; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
        .impact {{ background: white; padding: 15px; border-radius: 8px; }}
        .impact-row {{ display: flex; justify-content: space-between; padding: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Trading Recommendation</h1>
        <div class="ticker">{ticker}</div>
        <div>{exchange} • {recommendation.replace('_', ' ')}</div>
    </div>
    
    <div class="content">
        <div class="price-box">
            <div class="price">{currency} {current_price:.2f}</div>
            <div style="color: #6b7280;">CHF {price_chf:.2f}</div>
            <div style="margin-top: 10px;">{action_line}</div>
"""
        
        if position_value_chf:
            html += f'<div style="color: #6b7280;">Position value: CHF {position_value_chf:.2f}</div>'
        
        if stop_loss:
            html += f'<div style="color: #dc2626;">Stop-loss: {currency} {stop_loss:.2f}</div>'
        
        html += f"""
        </div>
        
        <div class="section">
            <div class="section-title">Analysis Scores</div>
            <div class="scores">
                <div class="score-item">
                    <div class="score-value">{analysis_scores.get('technical', 0):.0f}</div>
                    <div class="score-label">Technical</div>
                </div>
                <div class="score-item">
                    <div class="score-value">{analysis_scores.get('fundamental', 0):.0f}</div>
                    <div class="score-label">Fundamental</div>
                </div>
                <div class="score-item">
                    <div class="score-value">{analysis_scores.get('sentiment', 0):.0f}</div>
                    <div class="score-label">Sentiment</div>
                </div>
                <div class="score-item">
                    <div class="score-value">{analysis_scores.get('combined', 0):.0f}</div>
                    <div class="score-label">Combined</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Reasoning</div>
            <div class="reasoning">{reasoning}</div>
        </div>
        
        <div class="section">
            <div class="section-title">Portfolio Impact</div>
            <div class="impact">
                <div class="impact-row">
                    <span>Cash after trade:</span>
                    <strong>CHF {portfolio_impact.get('cash_after', 0):.2f}</strong>
                </div>
                <div class="impact-row">
                    <span>Total portfolio:</span>
                    <strong>CHF {portfolio_impact.get('total_portfolio', 0):.2f}</strong>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CET<br>
        Stock Trading Assistant
    </div>
</body>
</html>
"""
        return html
    
    def send_test_email(self) -> bool:
        """Send a test email to verify configuration"""
        if not self.is_configured():
            return False
        
        try:
            params = {
                "from": "Trading Assistant <onboarding@resend.dev>",
                "to": [self.recipient],
                "subject": "✅ Stock Trading Assistant - Test Email",
                "html": "<p>This is a test email from Stock Trading Assistant. Your email configuration is working correctly!</p>",
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Test email sent: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Test email failed: {e}")
            return False


_email_sender = None

def get_email_sender() -> EmailSender:
    """Get or create email sender singleton"""
    global _email_sender
    if _email_sender is None:
        _email_sender = EmailSender()
    return _email_sender
