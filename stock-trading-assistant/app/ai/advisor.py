"""
AI Chat module for portfolio advice using Claude
"""
import anthropic
from typing import Dict, Any, List, Optional
import json
import logging

from app.config import get_settings
from app.data.market_data import get_stock_info, get_historical_data
from app.data.forex import convert_to_chf, get_exchange_rate_to_chf
from app.analysis.engine import get_analysis_engine

settings = get_settings()
logger = logging.getLogger(__name__)


class AIAdvisor:
    """AI-powered portfolio advisor using Claude"""
    
    def __init__(self):
        self.api_key = settings.anthropic_api_key
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
        self.engine = get_analysis_engine()
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def chat(self, message: str, portfolio: Dict[str, Any]) -> str:
        """
        Chat with AI about portfolio decisions
        
        Args:
            message: User's question
            portfolio: Current portfolio data from PortfolioManager.get_portfolio_value()
        
        Returns:
            AI response
        """
        if not self.is_configured():
            return "AI chat is not configured. Please add ANTHROPIC_API_KEY to your environment variables."
        
        try:
            # Build context about the portfolio
            portfolio_context = self._build_portfolio_context(portfolio)
            
            # System prompt
            system_prompt = f"""You are an AI trading assistant helping a user manage their stock portfolio. 
You have access to their current portfolio and can analyze stocks.

CURRENT PORTFOLIO:
{portfolio_context}

USER'S BASE CURRENCY: CHF (Swiss Francs)
RISK ALLOCATION TARGET: 70% moderate, 30% aggressive

You can help with:
- Portfolio analysis and recommendations
- Suggesting new stocks to buy
- Analyzing when to sell positions
- Building diversified portfolios
- Explaining market conditions and stock analysis

When recommending stocks, be specific with:
- Ticker symbols and exchanges
- Number of shares based on available cash
- Risk category (conservative/moderate/aggressive)
- Brief reasoning

Always consider the user's available cash and current allocation when making recommendations.
Be concise but informative. Use CHF for all values."""

            # Check if user is asking about specific stocks - analyze them
            analysis_results = self._analyze_mentioned_stocks(message)
            
            if analysis_results:
                system_prompt += f"\n\nREAL-TIME ANALYSIS OF MENTIONED STOCKS:\n{analysis_results}"

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def _build_portfolio_context(self, portfolio: Dict[str, Any]) -> str:
        """Build a text summary of the portfolio for the AI"""
        lines = []
        
        lines.append(f"Total Value: CHF {portfolio.get('total_value_chf', 0):,.2f}")
        lines.append(f"Cash Available: CHF {portfolio.get('cash_chf', 0):,.2f}")
        lines.append(f"Holdings Value: CHF {portfolio.get('holdings_value_chf', 0):,.2f}")
        lines.append(f"Unrealized P&L: CHF {portfolio.get('unrealized_pnl_chf', 0):,.2f} ({portfolio.get('unrealized_pnl_pct', 0):.1f}%)")
        lines.append("")
        lines.append("HOLDINGS:")
        
        holdings = portfolio.get('holdings', [])
        if not holdings:
            lines.append("  (No holdings)")
        else:
            for h in holdings:
                lines.append(f"  {h['ticker']} ({h['exchange']}): {h['shares']:.0f} shares")
                lines.append(f"    Current: {h.get('current_currency', 'USD')} {h.get('current_price', 0):.2f} = CHF {h['current_value_chf']:,.2f}")
                lines.append(f"    P&L: CHF {h['unrealized_pnl_chf']:,.2f} ({h['unrealized_pnl_pct']:.1f}%)")
                lines.append(f"    Risk: {h['risk_category']}")
        
        return "\n".join(lines)
    
    def _analyze_mentioned_stocks(self, message: str) -> str:
        """Extract and analyze any stock tickers mentioned in the message"""
        # Common tickers to look for
        import re
        
        # Look for patterns like AAPL, NVDA, ITR.V, NESN.SW
        potential_tickers = re.findall(r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b', message.upper())
        
        # Filter out common words
        common_words = {'I', 'A', 'THE', 'AND', 'OR', 'TO', 'IN', 'FOR', 'ON', 'WITH', 'MY', 'IS', 'IT', 'BE', 'AS', 'AT', 'BY', 'IF', 'OF', 'SO', 'DO', 'AM', 'AN', 'AI', 'US', 'UK', 'EU', 'VS', 'CEO', 'CFO', 'IPO', 'ETF', 'USD', 'CHF', 'EUR', 'CAD', 'GBP', 'BUY', 'SELL', 'HOLD', 'NEW', 'ALL', 'WHAT', 'HOW', 'WHY', 'WHEN', 'CAN', 'YOU', 'YOUR'}
        tickers = [t for t in potential_tickers if t not in common_words]
        
        if not tickers:
            return ""
        
        # Limit to first 5 tickers
        tickers = tickers[:5]
        
        results = []
        for ticker in tickers:
            try:
                # Determine exchange
                exchange = ""
                if ".V" in ticker:
                    exchange = "TSX-V"
                elif ".SW" in ticker:
                    exchange = "SIX"
                elif ".TO" in ticker:
                    exchange = "TSX"
                
                analysis = self.engine.analyze_stock(ticker.replace(".V", "").replace(".SW", "").replace(".TO", ""), exchange)
                
                if "error" not in analysis:
                    results.append(f"""
{ticker}:
  Price: {analysis['currency']} {analysis['current_price']:.2f} (CHF {analysis['price_chf']:.2f})
  Recommendation: {analysis['recommendation']}
  Combined Score: {analysis['combined_score']:.0f}/100
  Technical: {analysis['technical']['score']:.0f} | Fundamental: {analysis['fundamental']['score']:.0f} | Sentiment: {analysis['sentiment']['score']:.0f}
  Risk Category: {analysis['risk_category']}
  Reasoning: {analysis['reasoning']}""")
            except Exception as e:
                logger.debug(f"Could not analyze {ticker}: {e}")
        
        return "\n".join(results)
    
    def suggest_portfolio(self, total_amount_chf: float, risk_profile: str = "balanced") -> str:
        """
        Generate a portfolio suggestion for a given amount
        
        Args:
            total_amount_chf: Amount to invest in CHF
            risk_profile: 'conservative', 'balanced', or 'aggressive'
        """
        if not self.is_configured():
            return "AI chat is not configured."
        
        prompt = f"""I have CHF {total_amount_chf:,.2f} to invest. 
My risk profile is {risk_profile}.
Please suggest a diversified portfolio with specific stocks, number of shares, and allocation percentages.
Include a mix of different sectors and geographies.
Format it clearly with ticker symbols, exchanges, and estimated costs in CHF."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="""You are a portfolio advisor. Suggest real, investable stocks available on major exchanges (NYSE, NASDAQ, TSX, SIX Swiss Exchange).
Be specific with ticker symbols and share counts. Calculate costs in CHF.
Consider current market conditions and diversification across sectors.""",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Portfolio suggestion error: {e}")
            return f"Error generating suggestion: {str(e)}"


_advisor = None

def get_ai_advisor() -> AIAdvisor:
    """Get or create AI advisor singleton"""
    global _advisor
    if _advisor is None:
        _advisor = AIAdvisor()
    return _advisor
