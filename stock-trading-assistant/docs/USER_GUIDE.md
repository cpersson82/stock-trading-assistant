# User Guide

## Overview

The Stock Trading Assistant monitors markets and generates recommendations based on technical, fundamental, and sentiment analysis. All portfolio values are shown in CHF.

## Dashboard

The main dashboard shows:

- **Total Portfolio Value**: Sum of holdings + cash in CHF
- **Holdings Value**: Current market value of all positions
- **Cash Available**: Your CHF cash balance
- **Today's Recommendations**: Count towards daily limit

### System Status

- **Active** (green): System is monitoring and will send recommendations
- **Paused** (yellow): System is monitoring but won't send emails

Click the status button to toggle.

### Manual Check

Click "Run Check" to immediately analyze holdings and scan for opportunities. Useful when you want to force an analysis outside scheduled times.

## Managing Holdings

### Adding a New Position

1. Go to Holdings page
2. Fill in the form:
   - **Ticker**: Stock symbol (e.g., AAPL, ITR)
   - **Exchange**: Where it trades (NYSE, NASDAQ, TSX-V, etc.)
   - **Shares**: Number of shares
   - **Purchase Price**: Your average cost per share
   - **Currency**: Currency of purchase price
   - **Purchase Date**: When you bought
   - **Risk Category**: Conservative, Moderate, or Aggressive

3. Click "Add Holding"

### Updating After a Trade

When you execute a trade on Interactive Brokers:

1. Go to Holdings page
2. Click "Edit" on the position
3. Update shares and/or average price
4. Save changes

### Recording a Sale

1. Update the shares to the new amount (or 0 if fully sold)
2. Or click "Delete" to remove the position entirely
3. Update your cash balance

### Cash Management

- Set cash balances for each currency you hold
- The system converts everything to CHF automatically
- Exchange rates update hourly

## Understanding Recommendations

### Recommendation Types

| Type | Score | Meaning |
|------|-------|---------|
| STRONG BUY | >75 | High confidence buy signal |
| BUY | >65 | Moderate buy signal |
| HOLD | 40-65 | No action recommended |
| SELL | <40 | Consider reducing position |
| STRONG SELL | <25 | High confidence sell signal |

### Analysis Components

1. **Technical Score (40%)**: Price trends, momentum indicators, volume patterns
2. **Fundamental Score (35%)**: Valuation, growth, profitability, financial health
3. **Sentiment Score (15%)**: News sentiment, unusual activity
4. **Risk-Adjusted Score (10%)**: Volatility consideration, diversification

### Reading a Recommendation

Each recommendation includes:
- **Action**: What to do (Buy X shares, Sell, Hold)
- **Price**: Current price when recommendation was made
- **Stop-Loss**: Suggested exit point to limit losses
- **Reasoning**: Why the recommendation was made
- **Scores**: Breakdown of each analysis component

## Email Notifications

Emails are sent when:
1. System is active (not paused)
2. Outside quiet hours (07:00-23:00 CET by default)
3. Daily limit not reached (3 by default)
4. A strong signal is detected

### Email Format

```
Subject: 🟢 [Buy] AAPL - Trading Recommendation

Recommendation: BUY
Ticker: AAPL
Exchange: NASDAQ
Current Price: USD 185.00 (CHF 163.50)

Recommended Action: Buy 10 shares
Position Value: CHF 1,635.00
Stop-Loss: USD 166.50

Reasoning: Technical indicators are bullish. Price above SMA200...

Analysis Scores:
- Technical: 72
- Fundamental: 68
- Sentiment: 55
- Combined: 68
```

## Analyzing Stocks

### Quick Analysis

1. Enter a ticker in the search box (top right)
2. Click "Go"
3. View the full analysis

### Analysis Page Shows:

- Current price and CHF equivalent
- Overall recommendation
- Combined score
- Detailed signals for each component
- Suggested action with position sizing

## Risk Management

### Position Sizing

The system recommends position sizes based on:
- Your total portfolio value
- Risk category of the stock
- Available cash
- Existing positions

Maximum position sizes:
- Conservative stocks: 25% of portfolio
- Moderate stocks: 15% of portfolio
- Aggressive stocks: 10% of portfolio

### Stop-Loss Recommendations

Suggested stop-losses are based on risk category:
- Conservative: 8% below entry
- Moderate: 12% below entry
- Aggressive: 18% below entry

## Tips for Best Results

1. **Execute promptly**: Recommendations are time-sensitive
2. **Use stop-losses**: Protect capital on volatile positions
3. **Check daily**: Review the dashboard even without recommendations
4. **Mark trades as executed**: Helps track recommendation performance
5. **Don't override the system**: If you have strong views, add them to your own analysis

## Troubleshooting

### No recommendations being generated

- Check that system is Active (not Paused)
- Verify you're outside quiet hours
- Check daily limit hasn't been reached
- Click "Run Check" to force analysis

### Incorrect portfolio value

- Verify all holdings have correct share counts
- Check that cash balances are accurate
- Exchange rates update hourly - try refreshing

### Analysis errors for a stock

- Some stocks have limited data (especially small caps)
- Try searching with a different exchange
- The stock may not be supported by Yahoo Finance
