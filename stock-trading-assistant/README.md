# Stock Trading Assistant

An AI-powered stock trading recommendation system that monitors global markets and sends actionable buy/sell/hold recommendations via email.

## Features

- **Multi-factor Analysis**: Combines technical, fundamental, and sentiment analysis
- **Global Market Coverage**: Supports US, Canadian, European, and Swiss exchanges
- **CHF Base Currency**: All portfolio values and returns calculated in Swiss Francs
- **Automated Monitoring**: Scheduled market checks at European open, US open, and US close
- **Email Notifications**: Automatic recommendations with detailed reasoning
- **Web Dashboard**: Clean interface for portfolio management and recommendation history
- **Risk Management**: Position sizing and stop-loss recommendations based on risk profile

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd stock-trading-assistant
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and set:
- `EMAIL_SENDER`: Your Gmail address
- `EMAIL_PASSWORD`: Gmail App Password (see docs/CONFIGURATION.md)
- `EMAIL_RECIPIENT`: Where to receive recommendations
- `SECRET_KEY`: Random string for security

### 3. Run Locally

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Visit http://localhost:8000

### 4. Initial Setup

1. Go to **Holdings** page
2. Add your starting position (ITR.V, 4657 shares)
3. Set cash balance (CHF 800)
4. The system will start monitoring automatically

## Project Structure

```
stock-trading-assistant/
├── app/
│   ├── analysis/       # Technical, fundamental, sentiment analysis
│   ├── data/           # Market data fetching, forex, screening
│   ├── portfolio/      # Portfolio management
│   ├── notifications/  # Email sending
│   ├── scheduler/      # Automated market checks
│   └── web/            # Dashboard routes and templates
├── data/               # SQLite database
├── docs/               # Documentation
└── requirements.txt
```

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Step-by-step Railway deployment
- [Configuration Guide](docs/CONFIGURATION.md) - API keys and email setup
- [User Guide](docs/USER_GUIDE.md) - How to use the system

## Analysis Engine

The system uses a weighted scoring model (0-100 scale):

| Component | Weight | Description |
|-----------|--------|-------------|
| Technical | 40% | RSI, MACD, Moving Averages, Bollinger Bands |
| Fundamental | 35% | P/E, Growth, Margins, Financial Health |
| Sentiment | 15% | News sentiment, price action |
| Risk-Adjusted | 10% | Volatility, diversification |

### Recommendation Thresholds

- **Strong Buy**: Score > 75
- **Buy**: Score > 65
- **Hold**: Score 40-65
- **Sell**: Score < 40
- **Strong Sell**: Score < 25

## Risk Allocation

- **70% Moderate**: Established companies, lower volatility
- **30% Aggressive**: Growth stocks, higher risk opportunities

## Market Checks Schedule (CET)

- 08:00 - European market open
- 15:30 - US market open
- 22:00 - US market close

## License

MIT
