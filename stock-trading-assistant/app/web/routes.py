"""
Web dashboard routes
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import json

from app.database import get_db, Holding, Recommendation, CashBalance, get_or_create_setting, update_setting, RiskCategory
from app.portfolio.manager import PortfolioManager
from app.scheduler.jobs import get_market_monitor
from app.notifications.email import get_email_sender
from app.data.forex import get_all_rates
from app.ai.advisor import get_ai_advisor
from app.config import get_settings

settings = get_settings()

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page"""
    portfolio_mgr = PortfolioManager(db)
    portfolio = portfolio_mgr.get_portfolio_value()
    allocation = portfolio_mgr.get_allocation_breakdown()
    performance = portfolio_mgr.get_performance_history(days=30)
    
    # Get recent recommendations
    recent_recommendations = db.query(Recommendation).order_by(
        Recommendation.created_at.desc()
    ).limit(10).all()
    
    # Get system status
    is_active = get_or_create_setting(db, "system_active", "true").lower() == "true"
    
    # Get daily recommendation count
    today = datetime.now().date()
    daily_count = db.query(Recommendation).filter(
        Recommendation.created_at >= datetime.combine(today, datetime.min.time()),
        Recommendation.email_sent == True
    ).count()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "portfolio": portfolio,
        "allocation": allocation,
        "performance": json.dumps(performance),
        "recommendations": recent_recommendations,
        "is_active": is_active,
        "daily_recommendation_count": daily_count,
        "max_daily_recommendations": settings.max_daily_recommendations,
        "email_configured": get_email_sender().is_configured(),
    })


@router.get("/holdings", response_class=HTMLResponse)
async def holdings_page(request: Request, db: Session = Depends(get_db)):
    """Holdings management page"""
    portfolio_mgr = PortfolioManager(db)
    portfolio = portfolio_mgr.get_portfolio_value()
    
    # Get cash balances
    cash_balances = db.query(CashBalance).all()
    
    # Get exchange rates
    rates = get_all_rates()
    
    return templates.TemplateResponse("holdings.html", {
        "request": request,
        "portfolio": portfolio,
        "cash_balances": cash_balances,
        "exchange_rates": rates,
    })


@router.post("/holdings/add")
async def add_holding(
    request: Request,
    ticker: str = Form(...),
    exchange: str = Form(...),
    shares: float = Form(...),
    purchase_price: float = Form(...),
    purchase_currency: str = Form(...),
    purchase_date: str = Form(...),
    risk_category: str = Form("moderate"),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """Add a new holding"""
    try:
        portfolio_mgr = PortfolioManager(db)
        
        # Parse date
        pdate = datetime.strptime(purchase_date, "%Y-%m-%d")
        
        portfolio_mgr.add_holding(
            ticker=ticker.upper(),
            exchange=exchange,
            shares=shares,
            purchase_price=purchase_price,
            purchase_currency=purchase_currency,
            purchase_date=pdate,
            risk_category=risk_category,
            notes=notes if notes else None
        )
        
        return RedirectResponse(url="/holdings", status_code=303)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/holdings/update/{ticker}")
async def update_holding(
    ticker: str,
    shares: Optional[float] = Form(None),
    purchase_price: Optional[float] = Form(None),
    risk_category: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Update an existing holding"""
    try:
        portfolio_mgr = PortfolioManager(db)
        
        holding = portfolio_mgr.update_holding(
            ticker=ticker,
            shares=shares,
            purchase_price=purchase_price,
            risk_category=risk_category,
            notes=notes
        )
        
        if not holding:
            raise HTTPException(status_code=404, detail="Holding not found")
        
        return RedirectResponse(url="/holdings", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/holdings/delete/{ticker}")
async def delete_holding(ticker: str, db: Session = Depends(get_db)):
    """Delete a holding"""
    portfolio_mgr = PortfolioManager(db)
    
    if not portfolio_mgr.remove_holding(ticker):
        raise HTTPException(status_code=404, detail="Holding not found")
    
    return RedirectResponse(url="/holdings", status_code=303)


@router.post("/cash/set")
async def set_cash_balance(
    amount: float = Form(...),
    currency: str = Form("CHF"),
    db: Session = Depends(get_db)
):
    """Set cash balance"""
    portfolio_mgr = PortfolioManager(db)
    portfolio_mgr.set_cash_balance(amount, currency)
    return RedirectResponse(url="/holdings", status_code=303)


@router.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request, db: Session = Depends(get_db)):
    """Recommendations history page"""
    recommendations = db.query(Recommendation).order_by(
        Recommendation.created_at.desc()
    ).limit(50).all()
    
    return templates.TemplateResponse("recommendations.html", {
        "request": request,
        "recommendations": recommendations,
    })


@router.post("/recommendations/{rec_id}/mark-executed")
async def mark_recommendation_executed(
    rec_id: int,
    execution_price: float = Form(...),
    db: Session = Depends(get_db)
):
    """Mark a recommendation as executed"""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    rec.executed = True
    rec.execution_price = execution_price
    rec.execution_date = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url="/recommendations", status_code=303)


@router.get("/analyze/{ticker}", response_class=HTMLResponse)
async def analyze_stock(
    request: Request,
    ticker: str,
    exchange: str = "",
    db: Session = Depends(get_db)
):
    """Analyze a specific stock"""
    monitor = get_market_monitor()
    analysis = monitor.analyze_single_stock(ticker, exchange)
    
    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "ticker": ticker,
        "exchange": exchange,
        "analysis": analysis,
    })


@router.post("/analyze", response_class=HTMLResponse)
async def analyze_stock_form(
    request: Request,
    ticker: str = Form(...),
    exchange: str = Form(""),
    db: Session = Depends(get_db)
):
    """Analyze a stock from form submission"""
    return RedirectResponse(
        url=f"/analyze/{ticker.upper()}?exchange={exchange}",
        status_code=303
    )


@router.post("/settings/toggle-active")
async def toggle_system_active(db: Session = Depends(get_db)):
    """Toggle system active/paused"""
    current = get_or_create_setting(db, "system_active", "true")
    new_value = "false" if current.lower() == "true" else "true"
    update_setting(db, "system_active", new_value)
    return RedirectResponse(url="/", status_code=303)


@router.post("/settings/test-email")
async def test_email(db: Session = Depends(get_db)):
    """Send a test email"""
    email_sender = get_email_sender()
    
    if not email_sender.is_configured():
        raise HTTPException(status_code=400, detail="Email not configured")
    
    success = email_sender.send_test_email()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send test email")
    
    return RedirectResponse(url="/", status_code=303)


@router.post("/run-check")
async def run_manual_check(db: Session = Depends(get_db)):
    """Manually trigger a market check"""
    try:
        monitor = get_market_monitor()
        monitor.run_market_check()
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio")
async def api_portfolio(db: Session = Depends(get_db)):
    """API endpoint for portfolio data"""
    portfolio_mgr = PortfolioManager(db)
    return portfolio_mgr.get_portfolio_value()


@router.get("/api/performance")
async def api_performance(days: int = 30, db: Session = Depends(get_db)):
    """API endpoint for performance history"""
    portfolio_mgr = PortfolioManager(db)
    return portfolio_mgr.get_performance_history(days)


@router.get("/api/analyze/{ticker}")
async def api_analyze(ticker: str, exchange: str = "", db: Session = Depends(get_db)):
    """API endpoint for stock analysis"""
    monitor = get_market_monitor()
    return monitor.analyze_single_stock(ticker, exchange)


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):
    """AI Chat page"""
    advisor = get_ai_advisor()
    portfolio_mgr = PortfolioManager(db)
    portfolio = portfolio_mgr.get_portfolio_value()
    
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "portfolio": portfolio,
        "ai_configured": advisor.is_configured(),
    })


@router.post("/api/chat")
async def api_chat(
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    """API endpoint for AI chat"""
    advisor = get_ai_advisor()
    
    if not advisor.is_configured():
        return {"error": "AI not configured. Add ANTHROPIC_API_KEY to environment."}
    
    portfolio_mgr = PortfolioManager(db)
    portfolio = portfolio_mgr.get_portfolio_value()
    
    response = advisor.chat(message, portfolio)
    
    return {"response": response}
