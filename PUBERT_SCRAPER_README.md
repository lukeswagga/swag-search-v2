# Pubert Custom Scraper

## Overview

The Pubert scraper is a **customer-specific scraper** that operates completely independently from the main brand flow. It:

- ✅ Uses its own brand list (`pubert_brands.json`)
- ✅ Posts ONLY to Discord channel `#pubert` (no emoji prefix)
- ✅ Does NOT interfere with main brand routing
- ✅ Does NOT post to auction-alerts, brand channels, or tier system
- ✅ Completely isolated from main scraper operations

## Components

### 1. pubert_brands.json
Contains 16 Japanese fashion brands specific to this customer:
- SHELLAC
- 14th Addiction
- Yasuyuki Ishii
- ISAMUKATAYAMA BACKLASH
- MIDAS
- TORNADO MART
- SCHLUSSEL
- JACKROSE
- VICE FAIRY
- goa
- KMRii
- LGB
- Buffalo Bobs
- 5351 pour les hommes
- obelisk
- Mihara yasuhiro

### 2. pubert_scraper.py
Custom scraper that:
- Inherits from `YahooScraperBase`
- Overrides `load_brand_data()` to load `pubert_brands.json`
- Sets `scraper_source = 'pubert_scraper'`
- Runs every 15 minutes (less frequent than main scrapers)
- Conservative pagination (max 2 pages initial, 1 page regular)

### 3. channel_router.py Updates
Added special routing logic for `pubert_scraper`:
- Skips daily digest
- Skips standard feed
- Skips auction-alerts channel
- Skips brand-specific channels
- **Routes ONLY to #pubert channel**

## Discord Channel Setup

**Important:** Create the Discord channel with this exact name:
```
#pubert
```

**NO emoji prefix** (unlike main brand channels which use 🏷️-)

The channel should be in your Discord server before deploying the scraper.

## Deployment Options

### Option 1: Separate Railway Service (Recommended)

Deploy as a completely separate service in Railway:

1. **Create new Railway service:**
   - In Railway dashboard, click "New Service"
   - Connect to your GitHub repo
   - Service name: `pubert-scraper`

2. **Set start command:**
   ```bash
   python pubert_scraper.py
   ```

3. **Environment variables:**
   Copy all env vars from main bot service:
   - `DISCORD_BOT_URL`
   - `PORT` (Railway sets this automatically)

4. **Deploy:**
   - Railway will auto-deploy
   - Check logs for: `🚀 Starting Pubert Custom Scraper`

### Option 2: Use Procfile.pubert

If you want to run alongside main bot in same service:

1. **Rename Procfile:**
   ```bash
   mv Procfile Procfile.main
   mv Procfile.pubert Procfile
   ```

2. **Deploy:**
   ```bash
   git add .
   git commit -m "Switch to Pubert scraper"
   git push
   ```

**Note:** This will REPLACE the main bot. Use Option 1 for parallel operation.

### Option 3: Manual Local Testing

For testing before deployment:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DISCORD_BOT_URL="your_bot_url"
export PORT=8000

# Run scraper
python pubert_scraper.py
```

## Verification

### Check Scraper is Running

Look for these log messages:

```
🚀 Starting Pubert Custom Scraper
👤 Customer: Pubert
🎯 Target Channel: #pubert
📦 Brands: 16
📅 Schedule: Every 15 minutes
📋 Pubert Brands Loaded:
   - SHELLAC
   - 14th Addiction
   - Yasuyuki Ishii
   ...
```

### Check Listings Being Sent

Watch for:

```
🔍 Processing Pubert listing: [title]...
   💰 Price: $XX.XX (¥XXX)
   🏷️ Brand: SHELLAC
   👤 Target: #pubert
✅ Sent Pubert listing to Discord bot: [title]...
```

### Check Discord Channel

In Discord `#pubert` channel, you should see listings appearing with:
- Brand names from pubert_brands.json
- Newest listings first
- Posted every 15 minutes

## Troubleshooting

### Listings not appearing in #pubert?

1. **Check channel exists:**
   - Channel must be named exactly `#pubert` (no emoji)
   - Bot needs "View Channel" and "Send Messages" permissions

2. **Check Railway logs:**
   ```
   👤 Pubert scraper detected - routing ONLY to #pubert channel
   ✅ Posted to #pubert
   ```

3. **If you see "Channel not found":**
   - Create the channel in Discord
   - Verify exact name: `pubert` (lowercase, no emoji)
   - Restart the scraper service

### Listings appearing in main channels?

This shouldn't happen! If you see Pubert brands in auction-alerts or brand channels:

1. **Check scraper_source:**
   - Should be `'pubert_scraper'` in all listings
   - Check pubert_scraper.py line 183: `listing['scraper_source'] = 'pubert_scraper'`

2. **Check channel_router.py:**
   - Lines 141-146: Should detect pubert_scraper and skip main routing

### No brands loading?

Check that `pubert_brands.json` exists in the same directory as `pubert_scraper.py`.

Expected output:
```
✅ Loading Pubert brands from pubert_brands.json
📋 Pubert Brands Loaded:
   - SHELLAC
   - 14th Addiction
   ...
```

## Architecture

```
pubert_scraper.py
    ↓
load pubert_brands.json (16 brands)
    ↓
scrape Yahoo Auctions (newest first)
    ↓
set scraper_source = 'pubert_scraper'
    ↓
send_to_discord()
    ↓
secure_discordbot.py webhook
    ↓
channel_router.route_listing()
    ↓
detect scraper_source == 'pubert_scraper'
    ↓
SKIP: daily digest, standard feed, auction-alerts, brand channels
    ↓
POST ONLY TO: #pubert channel
```

## Files Modified

- ✅ `pubert_brands.json` - New brand list (16 brands)
- ✅ `pubert_scraper.py` - New custom scraper
- ✅ `channel_router.py` - Updated routing logic
- ✅ `Procfile.pubert` - Deployment configuration
- ⚠️ **NOT MODIFIED:** brands.json, BRAND_CHANNEL_MAP, main Procfile

## Isolation Guarantees

The Pubert scraper is **completely isolated**:

1. **Separate brand list:** Uses `pubert_brands.json`, not `brands.json`
2. **Separate routing:** Special case in `channel_router.py`
3. **No tier system:** Skips digest, standard feed
4. **No main channels:** Skips auction-alerts, brand channels
5. **Single destination:** Only posts to `#pubert`
6. **Independent scraper:** Can be deployed separately in Railway

## Maintenance

### Adding New Brands

Edit `pubert_brands.json`:

```json
{
  "New Brand": {
    "variants": [
      "new brand",
      "ニューブランド"
    ],
    "subcategories": [
      "jacket", "pants", "shoes"
    ]
  }
}
```

**Important:** First variant should be Yahoo-friendly (lowercase, no special chars).

### Adjusting Frequency

Edit `pubert_scraper.py` line 300:

```python
# Change from 15 to desired minutes
schedule.every(15).minutes.do(self.run_pubert_cycle)
```

### Adjusting Page Count

Edit `pubert_scraper.py` lines 30-31:

```python
self.max_pages_initial = 2  # First few runs
self.max_pages_regular = 1  # Regular runs
```

## Support

If you need to:
- Add more brands → Edit `pubert_brands.json`
- Change frequency → Edit line 300 in `pubert_scraper.py`
- Create more customer scrapers → Clone this pattern with different channel name

The scraper is designed to be completely independent and won't affect your main operations.
