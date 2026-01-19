# Meyyjr Custom Scraper - Deployment Guide

## Overview
Customer-specific scraper for Discord channel **#meyyjr** with the following features:
- **10 Japanese fashion brands** (Issey Miyake, Yohji Yamamoto, Comme Des Garcons, Y's, ann demeulemeester, noir kei ninomiya, ground Y, Yoshiki Hishinuma, Limi feu, Vivienne Westwood)
- **Price Filter**: Maximum 60 EUR = ¥11,000 JPY
- **Sort Order**: Newest listings first (CRITICAL)
- **Listing Types**: Both auctions and fixed price
- **Isolation**: Posts ONLY to #meyyjr channel, does NOT interfere with main brand routing

## Critical Features

### 1. Price Filtering (60 EUR = ¥11,000 JPY)
All listings are filtered BEFORE being added to the seen items database:
- Items over ¥11,000 are blocked and logged
- Items under ¥11,000 are processed and sent
- Filtering statistics tracked in `price_blocked` counter

### 2. Newest-First Sorting
Uses Yahoo Auctions sorting parameters:
- `s1=new` (sort by new listings)
- `o1=d` (descending order - newest first)
- **CRITICAL**: Ensures customers see the freshest items

### 3. Isolated Routing
The scraper is completely isolated from the main bot:
- Uses `meyyjr_brands.json` (separate from main `brands.json`)
- Sets `scraper_source = 'meyyjr_scraper'`
- Posts ONLY to #meyyjr channel
- Skips daily digest and standard feed
- Skips main brand channels

## Deployment on Railway

### Step 1: Create Discord Channel
1. In your Discord server, create a text channel named: `meyyjr` (no emoji prefix)
2. Ensure the bot has permissions to post in this channel

### Step 2: Deploy to Railway
1. Go to Railway dashboard: https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `yahoo-japan-scraper` repository
4. Click "Add variables" and add:
   ```
   DISCORD_WEBHOOK_URL=<your_discord_webhook_url>
   DISCORD_BOT_TOKEN=<your_discord_bot_token>
   ```
5. In "Settings" → "Start Command", enter:
   ```
   python meyyjr_scraper.py
   ```
6. Or use the Procfile.meyyjr:
   - Rename `Procfile.meyyjr` to `Procfile` in deployment
   - Railway will auto-detect and use it

### Step 3: Verify Deployment
Monitor Railway logs for:
```
✅ Loading Meyyjr brands from meyyjr_brands.json
🚀 Starting Meyyjr Custom Scraper
👤 Customer: Meyyjr
🎯 Target Channel: #meyyjr
📦 Brands: 10
💰 Price Filter: Max ¥11,000 (60 EUR)
📅 Schedule: Every 15 minutes
🔄 Sort Order: NEWEST FIRST (critical)
⚠️ ISOLATED: Does not interfere with main brand routing
```

### Step 4: Monitor First Cycle
Look for price filtering logs:
```
✅ Price OK: ¥8,500 (under ¥11,000 limit)
🚫 Price filter: ¥15,000 exceeds ¥11,000 limit (60 EUR)
```

## Configuration

### Brand List (meyyjr_brands.json)
10 brands with Yahoo-friendly search variants:
1. **Issey Miyake** - includes pleats please, homme plisse variations
2. **Yohji Yamamoto** - includes Y-3, Y's
3. **Comme Des Garcons** - includes CDG variations
4. **Y's** - separate entry for Y's specific searches
5. **ann demeulemeester** - lowercase for search compatibility
6. **noir kei ninomiya** - includes Noir variations
7. **ground Y** - Yohji diffusion line
8. **Yoshiki Hishinuma** - technical avant-garde
9. **Limi feu** - Yohji daughter's line
10. **Vivienne Westwood** - punk/historical references

### Scraper Settings
```python
max_price_jpy = 11000  # 60 EUR
max_price_eur = 60
target_channel = "meyyjr"
max_pages_initial = 2  # First 3 cycles
max_pages_regular = 1  # After warmup
schedule = Every 15 minutes
```

### URL Parameters (Critical)
```python
fixed_type=3      # Both auctions and fixed price
sort_type="new"   # Sort by newest (CRITICAL)
sort_order="d"    # Descending (newest first)
page_size=50      # Conservative to avoid rate limits
```

## Troubleshooting

### Problem: No listings appearing
**Check:**
1. Discord channel name is exactly `meyyjr` (no emoji, no spaces)
2. Bot has permissions in #meyyjr channel
3. Railway logs show `🔍 Found: X items (after price filter)`
4. Check if all items are being price-filtered (logs show `🚫 Price filter`)

### Problem: Only expensive items showing
**Check:**
1. Verify `max_price_jpy = 11000` in logs
2. Look for price filtering logs: `✅ Price OK` vs `🚫 Price filter`
3. Check `price_blocked` counter in cycle summary

### Problem: Old listings appearing
**Check:**
1. Verify logs show `🔄 Sort Order: NEWEST FIRST (critical)`
2. Check URL in logs contains `s1=new&o1=d`
3. Ensure `sort_type="new"` and `sort_order="d"` in `build_search_url` calls

### Problem: Listings appearing in main channels
**Check:**
1. Verify `scraper_source = 'meyyjr_scraper'` in logs
2. Check channel_router.py includes meyyjr_scraper in isolation checks
3. Logs should show: `👤 meyyjr scraper detected - routing ONLY to #meyyjr channel`

### Problem: HTTP 500 errors
**Solution:**
- Already mitigated with sequential processing and retry logic
- 2.5s delays between pages, 3s delays between brands
- Exponential backoff on failures (2s, 4s, 8s, 16s)
- If persists, reduce `max_pages_regular` from 1 to 0 (initial cycle only)

## Monitoring

### Health Check
Railway provides a health endpoint on port 8000:
```
GET http://<your-railway-url>.railway.app/health
Response: {"status": "healthy", "scraper": "meyyjr_scraper"}
```

### Key Metrics (from cycle logs)
```
📊 Meyyjr Cycle #X Complete (ASYNC):
   ⏱️ Duration: XX.Xs
   🔍 Found: XX items (after price filter)
   📤 Sent: XX items
   💾 Tracking: XXX seen items
   💰 Price blocked: XX items  # Important metric
   🎯 Target: #meyyjr
   👤 Customer: Meyyjr
   📦 Brands: 10
```

## File Structure
```
yahoo-japan-scraper/
├── meyyjr_brands.json          # Isolated brand list (10 brands)
├── meyyjr_scraper.py           # Main scraper with price filtering
├── Procfile.meyyjr             # Railway deployment config
├── channel_router.py           # Updated with meyyjr routing
├── core_scraper_base.py        # Shared base class
└── MEYYJR_SCRAPER_README.md    # This file
```

## Comparison with Main Scrapers

| Feature | Main Scrapers | Meyyjr Scraper |
|---------|---------------|----------------|
| Brand List | brands.json (35+ brands) | meyyjr_brands.json (10 brands) |
| Price Filter | None | Max ¥11,000 (60 EUR) |
| Sort Order | Various (ending soon, etc.) | Newest first ONLY |
| Channels | Multiple (#auction-alerts, brand channels, digests) | ONLY #meyyjr |
| Isolation | Main bot flow | Completely isolated |
| Schedule | Varies by scraper | Every 15 minutes |

## Support

For issues or questions:
1. Check Railway logs for error messages
2. Verify Discord channel setup
3. Review channel_router.py routing logic
4. Check price filtering is working (look for 🚫 and ✅ logs)
