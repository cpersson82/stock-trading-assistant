"""
Data fetching and processing modules
"""
from app.data.market_data import (
    get_stock_info,
    get_historical_data,
    get_multiple_quotes,
    get_news_for_stock,
    is_market_open,
    MarketDataError,
)
from app.data.forex import (
    get_exchange_rate_to_chf,
    convert_to_chf,
    convert_from_chf,
    get_all_rates,
)
from app.data.screener import (
    get_screening_candidates,
    discover_opportunities,
)

__all__ = [
    "get_stock_info",
    "get_historical_data",
    "get_multiple_quotes",
    "get_news_for_stock",
    "is_market_open",
    "MarketDataError",
    "get_exchange_rate_to_chf",
    "convert_to_chf",
    "convert_from_chf",
    "get_all_rates",
    "get_screening_candidates",
    "discover_opportunities",
]
