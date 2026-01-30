# Deployment Guide

This guide walks you through deploying the Stock Trading Assistant to Railway.

## Prerequisites

- GitHub account
- Railway account (free at railway.app)
- Gmail account for notifications

## Step 1: Prepare Your Repository

1. **Create a new GitHub repository**
   - Go to github.com → New repository
   - Name it `stock-trading-assistant`
   - Make it private (recommended)

2. **Push the code**
   ```bash
   cd stock-trading-assistant
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/stock-trading-assistant.git
   git push -u origin main
   ```

## Step 2: Deploy to Railway

1. **Go to Railway**
   - Visit [railway.app](https://railway.app)
   - Sign in with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `stock-trading-assistant` repository

3. **Configure Environment Variables**
   
   Click on your service → Variables → Add these:

   ```
   EMAIL_SENDER=your-gmail@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_RECIPIENT=your-gmail@gmail.com
   SECRET_KEY=generate-a-random-string-here
   ALPHA_VANTAGE_API_KEY=demo
   ```

   **To generate SECRET_KEY**, you can use:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Deploy**
   - Railway will automatically detect the Procfile and deploy
   - Wait for the build to complete (2-3 minutes)

5. **Get Your URL**
   - Go to Settings → Domains
   - Click "Generate Domain"
   - Your app will be at `https://your-app.railway.app`

## Step 3: Initial Configuration

1. **Access the Dashboard**
   - Open your Railway URL in a browser
   - You should see the Stock Trading Assistant dashboard

2. **Add Your Holdings**
   - Go to Holdings page
   - Add ITR.V:
     - Ticker: `ITR`
     - Exchange: `TSX-V`
     - Shares: `4657`
     - Purchase Price: `5.71` (using current price as cost basis)
     - Currency: `CAD`
     - Purchase Date: Today's date
     - Risk Category: `aggressive`

3. **Set Cash Balance**
   - On the Holdings page
   - Set CHF balance to `800`

4. **Test Email**
   - On the Dashboard, click "Send Test Email"
   - Verify you receive it

## Step 4: Verify Operation

1. **Manual Check**
   - Click "Run Check" on the dashboard
   - This will analyze your holdings and scan for opportunities
   - Check the Recommendations page for any new entries

2. **Check Logs**
   - In Railway, go to your service → Deployments → View Logs
   - You should see scheduled job messages

## Troubleshooting

### App won't start

Check the logs in Railway. Common issues:
- Missing environment variables
- Incorrect EMAIL_PASSWORD format

### Emails not sending

1. Make sure you're using a Gmail App Password, not your regular password
2. Check that EMAIL_SENDER and EMAIL_PASSWORD are set correctly
3. Try the "Send Test Email" button

### Analysis errors

Some stocks may not have complete data. Check:
- Ticker symbol is correct
- Exchange is correct
- Stock is actively traded

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Railway (Hobby) | $5-10 |
| Market Data APIs | $0 (free tiers) |
| Gmail SMTP | $0 |
| **Total** | **~$5-10/month** |

## Updating the Application

1. Make changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
3. Railway will automatically redeploy

## Backup Your Data

The SQLite database is stored at `data/trading.db`. To backup:

1. In Railway, go to your service
2. Use the Railway CLI to download:
   ```bash
   railway run cat data/trading.db > backup.db
   ```

Or add a PostgreSQL database for persistent storage (recommended for production).
