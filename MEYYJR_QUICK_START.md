# Meyyjr Scraper - Quick Start Guide

## What is This?
Customer-specific scraper that posts Japanese fashion listings to Discord channel **#meyyjr** with:
- ✅ Price filter: Max 60 EUR (¥11,000)
- ✅ Sort: Newest listings first
- ✅ 10 Brands: Issey Miyake, Yohji Yamamoto, Comme Des Garcons, Y's, ann demeulemeester, noir kei ninomiya, ground Y, Yoshiki Hishinuma, Limi feu, Vivienne Westwood
- ✅ Isolated: Does NOT interfere with main bot

## Deploy in 5 Minutes

### 1. Create Discord Channel
In your Discord server:
- Create text channel: `meyyjr` (no emoji prefix)
- Give bot permission to post

### 2. Deploy on Railway
```bash
# Railway Dashboard
1. New Project → Deploy from GitHub
2. Select: yahoo-japan-scraper repo
3. Settings → Start Command: python meyyjr_scraper.py
4. Add environment variables:
   - DISCORD_WEBHOOK_URL=<your_webhook>
   - DISCORD_BOT_TOKEN=<your_token>
5. Deploy
```

### 3. Verify It's Working
Check Railway logs for:
```
✅ Loading Meyyjr brands from meyyjr_brands.json
🚀 Starting Meyyjr Custom Scraper
👤 Customer: Meyyjr
🎯 Target Channel: #meyyjr
💰 Price Filter: Max ¥11,000 (60 EUR)
🔄 Sort Order: NEWEST FIRST (critical)
```

### 4. Monitor First Listings
In #meyyjr channel, you should see:
- Listings under ¥11,000 only
- Newest listings first
- From 10 configured brands only

## Price Filtering Logs
```
✅ Price OK: ¥8,500 (under ¥11,000 limit)     ← Will be posted
🚫 Price filter: ¥15,000 exceeds ¥11,000 limit ← Blocked
```

## Key Features

### 🎯 Isolated Routing
- Posts ONLY to #meyyjr
- Skips #auction-alerts, brand channels, daily digest, standard feed
- Uses separate brand list (meyyjr_brands.json)

### 💰 Price Filtering
- Max price: ¥11,000 (60 EUR)
- Filtered BEFORE adding to seen items
- Statistics tracked: `price_blocked` counter

### 🔄 Newest First
- Uses `s1=new&o1=d` parameters
- Ensures freshest listings
- Critical for time-sensitive deals

### 📦 Brand Coverage
10 avant-garde Japanese brands:
1. Issey Miyake (pleats please, homme plisse)
2. Yohji Yamamoto (Y-3, Y's)
3. Comme Des Garcons
4. Y's
5. ann demeulemeester
6. noir kei ninomiya
7. ground Y
8. Yoshiki Hishinuma
9. Limi feu
10. Vivienne Westwood

## Troubleshooting

### No Listings?
- Check channel name is exactly `meyyjr`
- Verify bot permissions in #meyyjr
- Check Railway logs for errors

### Only Expensive Items?
- Verify logs show `💰 Price Filter: Max ¥11,000`
- Look for `🚫 Price filter` logs
- Check `price_blocked` counter in cycle summary

### Old Listings?
- Verify logs show `🔄 Sort Order: NEWEST FIRST`
- Check URL contains `s1=new&o1=d`

### Appearing in Main Channels?
- Check logs for `👤 meyyjr scraper detected - routing ONLY to #meyyjr channel`
- Verify `scraper_source = 'meyyjr_scraper'` in logs

## Files
- `meyyjr_brands.json` - Brand list (10 brands)
- `meyyjr_scraper.py` - Main scraper with price filter
- `Procfile.meyyjr` - Railway deployment config
- `MEYYJR_SCRAPER_README.md` - Full documentation

## Schedule
Runs every **15 minutes** to catch new listings quickly while respecting Yahoo rate limits.

## Health Check
```bash
curl https://<your-railway-url>.railway.app/health
# Response: {"status": "healthy", "scraper": "meyyjr_scraper"}
```

## Support
See `MEYYJR_SCRAPER_README.md` for detailed troubleshooting and configuration.
