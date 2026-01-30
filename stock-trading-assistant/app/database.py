"""
Database models and connection management
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import enum
from typing import Generator
import os

from app.config import get_settings

settings = get_settings()

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class RecommendationType(str, enum.Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskCategory(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class Holding(Base):
    """Portfolio holdings"""
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    exchange = Column(String(20), nullable=False)
    shares = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)  # In original currency
    purchase_currency = Column(String(5), nullable=False)
    purchase_date = Column(DateTime, nullable=False)
    cost_basis_chf = Column(Float, nullable=False)  # Total cost in CHF
    risk_category = Column(SQLEnum(RiskCategory), default=RiskCategory.MODERATE)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Holding {self.ticker}: {self.shares} shares>"


class CashBalance(Base):
    """Cash balances in different currencies"""
    __tablename__ = "cash_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    currency = Column(String(5), unique=True, nullable=False)
    amount = Column(Float, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CashBalance {self.currency}: {self.amount}>"


class Recommendation(Base):
    """Trading recommendations history"""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    exchange = Column(String(20), nullable=False)
    recommendation_type = Column(SQLEnum(RecommendationType), nullable=False)
    
    # Price info at time of recommendation
    price_at_recommendation = Column(Float, nullable=False)
    price_currency = Column(String(5), nullable=False)
    price_in_chf = Column(Float, nullable=False)
    
    # Action details
    recommended_shares = Column(Float, nullable=True)  # None for HOLD
    recommended_value_chf = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    
    # Analysis scores
    technical_score = Column(Float, nullable=False)
    fundamental_score = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    combined_score = Column(Float, nullable=False)
    
    # Reasoning
    reasoning = Column(Text, nullable=False)
    
    # Status
    email_sent = Column(Boolean, default=False)
    executed = Column(Boolean, default=False)
    execution_price = Column(Float, nullable=True)
    execution_date = Column(DateTime, nullable=True)
    
    # Portfolio impact
    portfolio_value_before = Column(Float, nullable=True)
    portfolio_value_after = Column(Float, nullable=True)
    cash_after_trade = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Recommendation {self.recommendation_type.value} {self.ticker} @ {self.price_at_recommendation}>"


class PortfolioSnapshot(Base):
    """Daily portfolio value snapshots for performance tracking"""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True, nullable=False)
    total_value_chf = Column(Float, nullable=False)
    holdings_value_chf = Column(Float, nullable=False)
    cash_value_chf = Column(Float, nullable=False)
    daily_return_pct = Column(Float, nullable=True)
    cumulative_return_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PortfolioSnapshot {self.date}: CHF {self.total_value_chf}>"


class SystemSettings(Base):
    """System settings stored in database"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemSettings {self.key}={self.value}>"


class WatchlistItem(Base):
    """Stocks being monitored for opportunities"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    exchange = Column(String(20), nullable=False)
    added_reason = Column(Text, nullable=True)
    last_analyzed = Column(DateTime, nullable=True)
    last_score = Column(Float, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WatchlistItem {self.ticker}>"


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_setting(db: Session, key: str, default_value: str) -> str:
    """Get a setting or create with default if not exists"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if setting:
        return setting.value
    
    new_setting = SystemSettings(key=key, value=default_value)
    db.add(new_setting)
    db.commit()
    return default_value


def update_setting(db: Session, key: str, value: str) -> None:
    """Update a system setting"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = SystemSettings(key=key, value=value)
        db.add(setting)
    db.commit()
