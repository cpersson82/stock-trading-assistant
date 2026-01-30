"""
Portfolio management module
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
import logging

from app.database import Holding, CashBalance, PortfolioSnapshot, RiskCategory
from app.data.market_data import get_stock_info, get_multiple_quotes
from app.data.forex import convert_to_chf, get_exchange_rate_to_chf
from app.config import get_settings, EXCHANGE_INFO

settings = get_settings()
logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Manages portfolio holdings, valuations, and performance tracking
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_holdings(self) -> List[Holding]:
        """Get all current holdings"""
        return self.db.query(Holding).all()
    
    def get_holding(self, ticker: str) -> Optional[Holding]:
        """Get a specific holding by ticker"""
        return self.db.query(Holding).filter(Holding.ticker == ticker).first()
    
    def add_holding(
        self,
        ticker: str,
        exchange: str,
        shares: float,
        purchase_price: float,
        purchase_currency: str,
        purchase_date: datetime,
        risk_category: str = "moderate",
        notes: str = None
    ) -> Holding:
        """
        Add a new holding to the portfolio
        """
        # Calculate cost basis in CHF
        cost_basis_chf = convert_to_chf(purchase_price * shares, purchase_currency)
        
        # Check if holding already exists
        existing = self.get_holding(ticker)
        if existing:
            # Update existing holding (average cost)
            total_shares = existing.shares + shares
            total_cost = existing.cost_basis_chf + cost_basis_chf
            existing.shares = total_shares
            existing.cost_basis_chf = total_cost
            existing.purchase_price = total_cost / total_shares / get_exchange_rate_to_chf(purchase_currency)
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing
        
        # Create new holding
        holding = Holding(
            ticker=ticker.upper(),
            exchange=exchange,
            shares=shares,
            purchase_price=purchase_price,
            purchase_currency=purchase_currency,
            purchase_date=purchase_date,
            cost_basis_chf=cost_basis_chf,
            risk_category=RiskCategory(risk_category),
            notes=notes,
        )
        
        self.db.add(holding)
        self.db.commit()
        self.db.refresh(holding)
        
        return holding
    
    def update_holding(
        self,
        ticker: str,
        shares: Optional[float] = None,
        purchase_price: Optional[float] = None,
        risk_category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Holding]:
        """
        Update an existing holding
        """
        holding = self.get_holding(ticker)
        if not holding:
            return None
        
        if shares is not None:
            holding.shares = shares
        if purchase_price is not None:
            holding.purchase_price = purchase_price
            holding.cost_basis_chf = convert_to_chf(
                purchase_price * holding.shares,
                holding.purchase_currency
            )
        if risk_category is not None:
            holding.risk_category = RiskCategory(risk_category)
        if notes is not None:
            holding.notes = notes
        
        holding.updated_at = datetime.utcnow()
        self.db.commit()
        
        return holding
    
    def remove_holding(self, ticker: str) -> bool:
        """
        Remove a holding from the portfolio
        """
        holding = self.get_holding(ticker)
        if not holding:
            return False
        
        self.db.delete(holding)
        self.db.commit()
        return True
    
    def get_cash_balance(self, currency: str = "CHF") -> float:
        """Get cash balance in specified currency"""
        balance = self.db.query(CashBalance).filter(CashBalance.currency == currency).first()
        return balance.amount if balance else 0.0
    
    def set_cash_balance(self, amount: float, currency: str = "CHF") -> CashBalance:
        """Set cash balance for a currency"""
        balance = self.db.query(CashBalance).filter(CashBalance.currency == currency).first()
        
        if balance:
            balance.amount = amount
            balance.updated_at = datetime.utcnow()
        else:
            balance = CashBalance(currency=currency, amount=amount)
            self.db.add(balance)
        
        self.db.commit()
        return balance
    
    def adjust_cash(self, amount: float, currency: str = "CHF") -> float:
        """Adjust cash balance by amount (positive or negative)"""
        current = self.get_cash_balance(currency)
        new_amount = current + amount
        self.set_cash_balance(new_amount, currency)
        return new_amount
    
    def get_total_cash_chf(self) -> float:
        """Get total cash across all currencies in CHF"""
        balances = self.db.query(CashBalance).all()
        total = 0.0
        
        for balance in balances:
            total += convert_to_chf(balance.amount, balance.currency)
        
        return total
    
    def get_portfolio_value(self) -> Dict[str, Any]:
        """
        Calculate current portfolio value with live prices
        
        Returns:
            Dict with holdings values, cash, and total
        """
        holdings = self.get_holdings()
        
        if not holdings:
            cash_chf = self.get_total_cash_chf()
            return {
                "holdings": [],
                "holdings_value_chf": 0,
                "cash_chf": cash_chf,
                "total_value_chf": cash_chf,
                "unrealized_pnl_chf": 0,
                "unrealized_pnl_pct": 0,
            }
        
        # Fetch current prices
        tickers = [(h.ticker, h.exchange) for h in holdings]
        quotes = get_multiple_quotes(tickers)
        
        holdings_data = []
        total_holdings_value = 0
        total_cost_basis = 0
        
        for holding in holdings:
            quote = quotes.get(holding.ticker, {})
            current_price = quote.get("current_price", 0)
            currency = quote.get("currency", holding.purchase_currency)
            
            if current_price:
                current_value = current_price * holding.shares
                current_value_chf = convert_to_chf(current_value, currency)
            else:
                # Fallback to purchase price if no quote
                current_value = holding.purchase_price * holding.shares
                current_value_chf = holding.cost_basis_chf
                currency = holding.purchase_currency
            
            unrealized_pnl_chf = current_value_chf - holding.cost_basis_chf
            unrealized_pnl_pct = (unrealized_pnl_chf / holding.cost_basis_chf * 100) if holding.cost_basis_chf else 0
            
            holdings_data.append({
                "ticker": holding.ticker,
                "exchange": holding.exchange,
                "shares": holding.shares,
                "purchase_price": holding.purchase_price,
                "purchase_currency": holding.purchase_currency,
                "current_price": current_price,
                "current_currency": currency,
                "cost_basis_chf": holding.cost_basis_chf,
                "current_value_chf": current_value_chf,
                "unrealized_pnl_chf": unrealized_pnl_chf,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "risk_category": holding.risk_category.value,
                "daily_change": quote.get("daily_change"),
                "daily_change_pct": quote.get("daily_change_pct"),
            })
            
            total_holdings_value += current_value_chf
            total_cost_basis += holding.cost_basis_chf
        
        cash_chf = self.get_total_cash_chf()
        total_value = total_holdings_value + cash_chf
        total_unrealized_pnl = total_holdings_value - total_cost_basis
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis else 0
        
        return {
            "holdings": holdings_data,
            "holdings_value_chf": round(total_holdings_value, 2),
            "cash_chf": round(cash_chf, 2),
            "total_value_chf": round(total_value, 2),
            "cost_basis_chf": round(total_cost_basis, 2),
            "unrealized_pnl_chf": round(total_unrealized_pnl, 2),
            "unrealized_pnl_pct": round(total_unrealized_pnl_pct, 2),
        }
    
    def get_allocation_breakdown(self) -> Dict[str, Any]:
        """
        Get portfolio allocation by risk category
        """
        portfolio = self.get_portfolio_value()
        total_value = portfolio["total_value_chf"]
        
        if total_value <= 0:
            return {
                "conservative": 0,
                "moderate": 0,
                "aggressive": 0,
                "cash": 100,
            }
        
        allocations = {
            "conservative": 0,
            "moderate": 0,
            "aggressive": 0,
        }
        
        for holding in portfolio["holdings"]:
            risk = holding["risk_category"]
            pct = (holding["current_value_chf"] / total_value) * 100
            allocations[risk] = allocations.get(risk, 0) + pct
        
        allocations["cash"] = (portfolio["cash_chf"] / total_value) * 100
        
        # Round all values
        return {k: round(v, 1) for k, v in allocations.items()}
    
    def record_snapshot(self) -> PortfolioSnapshot:
        """
        Record a portfolio snapshot for performance tracking
        """
        portfolio = self.get_portfolio_value()
        
        # Get previous snapshot for return calculation
        prev_snapshot = self.db.query(PortfolioSnapshot).order_by(
            PortfolioSnapshot.date.desc()
        ).first()
        
        daily_return = None
        cumulative_return = None
        
        if prev_snapshot and prev_snapshot.total_value_chf > 0:
            daily_return = ((portfolio["total_value_chf"] - prev_snapshot.total_value_chf) 
                          / prev_snapshot.total_value_chf) * 100
            
            # Get first snapshot for cumulative return
            first_snapshot = self.db.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.date.asc()
            ).first()
            
            if first_snapshot and first_snapshot.total_value_chf > 0:
                cumulative_return = ((portfolio["total_value_chf"] - first_snapshot.total_value_chf)
                                   / first_snapshot.total_value_chf) * 100
        
        snapshot = PortfolioSnapshot(
            date=datetime.utcnow(),
            total_value_chf=portfolio["total_value_chf"],
            holdings_value_chf=portfolio["holdings_value_chf"],
            cash_value_chf=portfolio["cash_chf"],
            daily_return_pct=daily_return,
            cumulative_return_pct=cumulative_return,
        )
        
        self.db.add(snapshot)
        self.db.commit()
        
        return snapshot
    
    def get_performance_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get portfolio performance history
        """
        snapshots = self.db.query(PortfolioSnapshot).order_by(
            PortfolioSnapshot.date.desc()
        ).limit(days).all()
        
        return [
            {
                "date": s.date.isoformat(),
                "total_value_chf": s.total_value_chf,
                "holdings_value_chf": s.holdings_value_chf,
                "cash_value_chf": s.cash_value_chf,
                "daily_return_pct": s.daily_return_pct,
                "cumulative_return_pct": s.cumulative_return_pct,
            }
            for s in reversed(snapshots)
        ]
    
    def check_position_limits(
        self,
        ticker: str,
        proposed_value_chf: float
    ) -> Tuple[bool, str]:
        """
        Check if a proposed position meets allocation limits
        
        Returns:
            (is_allowed, reason)
        """
        portfolio = self.get_portfolio_value()
        total_value = portfolio["total_value_chf"]
        
        if total_value <= 0:
            return True, "Portfolio empty"
        
        # Get existing position
        existing_value = 0
        existing_risk = "moderate"
        for h in portfolio["holdings"]:
            if h["ticker"] == ticker:
                existing_value = h["current_value_chf"]
                existing_risk = h["risk_category"]
                break
        
        new_total_position = existing_value + proposed_value_chf
        position_pct = (new_total_position / total_value) * 100
        
        # Check individual position limit
        max_position_pct = {
            "conservative": 25,
            "moderate": 15,
            "aggressive": 10,
        }.get(existing_risk, 15)
        
        if position_pct > max_position_pct:
            return False, f"Position would exceed {max_position_pct}% limit for {existing_risk} risk"
        
        # Check overall allocation limits
        allocation = self.get_allocation_breakdown()
        
        # Aggressive allocation limit (30%)
        if existing_risk == "aggressive":
            if allocation["aggressive"] + (proposed_value_chf / total_value * 100) > 35:
                return False, "Would exceed 30% aggressive allocation limit"
        
        return True, "Within limits"
