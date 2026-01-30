# Configuration Guide

## Gmail App Password Setup

The system uses Gmail SMTP to send recommendations. You'll need an App Password (not your regular password).

### Step 1: Enable 2-Factor Authentication

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click "Security" in the left sidebar
3. Under "Signing in to Google", click "2-Step Verification"
4. Follow the prompts to enable it

### Step 2: Generate App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sign in if prompted
3. Under "Select app", choose "Other (Custom name)"
4. Enter "Stock Trading Assistant"
5. Click "Generate"
6. **Copy the 16-character password** (format: xxxx xxxx xxxx xxxx)
7. Use this as `EMAIL_PASSWORD` in your .env file (without spaces)

### Example

```env
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
EMAIL_RECIPIENT=your-email@gmail.com
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_SENDER` | Yes | - | Gmail address for sending emails |
| `EMAIL_PASSWORD` | Yes | - | Gmail App Password |
| `EMAIL_RECIPIENT` | Yes | - | Email to receive recommendations |
| `SECRET_KEY` | Yes | - | Random string for session security |
| `ALPHA_VANTAGE_API_KEY` | No | demo | Alpha Vantage API key |
| `FINNHUB_API_KEY` | No | - | Finnhub API key (optional) |
| `USER_TIMEZONE` | No | Europe/Zurich | Your timezone |
| `BASE_CURRENCY` | No | CHF | Base currency for valuations |
| `MAX_DAILY_RECOMMENDATIONS` | No | 3 | Max recommendations per day |
| `QUIET_HOURS_START` | No | 23 | No emails after this hour |
| `QUIET_HOURS_END` | No | 7 | No emails before this hour |
| `MODERATE_ALLOCATION` | No | 0.70 | Target moderate allocation |
| `AGGRESSIVE_ALLOCATION` | No | 0.30 | Target aggressive allocation |

## Market Data APIs

### Yahoo Finance (Free - Primary)

Used for:
- Real-time quotes
- Historical data
- Fundamentals
- News

No API key required. Rate limits are generous for personal use.

### Alpha Vantage (Free Tier)

Used for:
- Backup data source
- Forex rates

Get a free key at [alphavantage.co](https://www.alphavantage.co/support/#api-key)

Free tier: 500 API calls per day

### Finnhub (Optional)

Used for:
- Additional news sentiment
- Company profiles

Get a free key at [finnhub.io](https://finnhub.io/)

Free tier: 60 API calls per minute

## Customizing Risk Allocation

Edit the following in `.env`:

```env
# 70% moderate, 30% aggressive
MODERATE_ALLOCATION=0.70
AGGRESSIVE_ALLOCATION=0.30
```

Alternative allocations:
- Conservative: `MODERATE_ALLOCATION=0.80`, `AGGRESSIVE_ALLOCATION=0.20`
- Aggressive: `MODERATE_ALLOCATION=0.50`, `AGGRESSIVE_ALLOCATION=0.50`

## Adjusting Recommendation Limits

```env
# Allow up to 5 recommendations per day
MAX_DAILY_RECOMMENDATIONS=5

# Quiet hours: no emails between 22:00 and 08:00
QUIET_HOURS_START=22
QUIET_HOURS_END=8
```

## Database Configuration

By default, SQLite is used. The database file is at `data/trading.db`.

For production with persistent storage, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

On Railway, you can add a PostgreSQL database and use the provided connection string.
