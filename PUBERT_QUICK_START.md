# Pubert Scraper - Quick Start Guide

## ✅ What's Been Added

**5 new files committed and pushed to GitHub:**

1. **pubert_brands.json** - 16 Japanese brands for Pubert customer
2. **pubert_scraper.py** - Isolated custom scraper
3. **channel_router.py** - Updated with Pubert routing (skips all main channels)
4. **Procfile.pubert** - Deployment configuration
5. **PUBERT_SCRAPER_README.md** - Complete documentation

## 🚀 Quick Deployment (Railway)

### Step 1: Create Discord Channel

In your Discord server, create a new text channel:
- **Name:** `pubert` (exact, lowercase, NO emoji)
- **Category:** Any (or create "Custom Customers")
- **Permissions:** Bot needs "View Channel" and "Send Messages"

### Step 2: Deploy to Railway

**Option A: New Separate Service (Recommended)**

1. Go to Railway dashboard
2. Click "New Service"
3. Connect to your GitHub repo: `lukeswagga/yahoo-japan-scraper`
4. Select branch: `claude/fix-yahoo-500-errors-AXPJL` (or merge to main first)
5. **Service Name:** `pubert-scraper`
6. **Start Command:** `python pubert_scraper.py`
7. **Environment Variables:** Copy from main bot service
   - `DISCORD_BOT_URL` = (your Discord bot URL)
   - `PORT` = (Railway sets automatically)
8. Click "Deploy"

**Option B: Replace Main Bot (Not Recommended)**

If you want to test locally or replace your current scraper:
1. In Railway, find your scraper service
2. Go to Settings → Start Command
3. Change to: `python pubert_scraper.py`
4. Redeploy

## ✅ Verification Checklist

### 1. Check Railway Logs

You should see:
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
   - ISAMUKATAYAMA BACKLASH
   ...
```

### 2. Wait 15 Minutes

First scrape cycle runs immediately, then every 15 minutes.

### 3. Check Discord #pubert Channel

You should see listings like:
```
[Title in Japanese/English]
🏷️ Brand: SHELLAC
💰 Price: ¥XX,XXX ($XX.XX)
⭐ Quality: XX%
🔍 Source: Pubert Scraper
🔗 Links: Yahoo Japan | Buyee | ZenMarket
```

### 4. Verify Isolation

**Check that Pubert listings DO NOT appear in:**
- ❌ #🎯-auction-alerts
- ❌ Brand channels (e.g., #🏷️-lgb)
- ❌ #daily-digest
- ❌ #standard-feed

**Only in:**
- ✅ #pubert

## 📊 Expected Behavior

| Aspect | Behavior |
|--------|----------|
| **Frequency** | Every 15 minutes |
| **Target Channel** | #pubert only |
| **Brands** | 16 Japanese brands from pubert_brands.json |
| **Sort Order** | Newest listings first |
| **Pages Scraped** | 2 pages initially, 1 page regularly |
| **Items per Page** | 50 |
| **Isolation** | Complete - no interference with main flow |

## 🔧 Troubleshooting

### No listings appearing?

1. **Check Discord channel exists:**
   ```
   Channel name: pubert
   Not: #Pubert, #PUBERT, #🏷️-pubert
   ```

2. **Check Railway logs for errors:**
   ```bash
   # Look for:
   ⚠️ Channel #pubert not found
   ```

3. **Verify bot permissions:**
   - Bot must have "View Channel" and "Send Messages" in #pubert

### Listings appearing in main channels?

This shouldn't happen! If it does:
1. Check channel_router.py was deployed correctly
2. Check Railway logs show: `👤 Pubert scraper detected - routing ONLY to #pubert channel`
3. Restart the service

### Brands not loading?

Check Railway logs for:
```
✅ Loading Pubert brands from pubert_brands.json
```

If you see:
```
❌ pubert_brands.json not found!
```

Then the file wasn't deployed. Redeploy from the correct branch.

## 📝 Next Steps

### To Add More Brands

1. Edit `pubert_brands.json` in GitHub
2. Add new brand:
   ```json
   {
     "New Brand Name": {
       "variants": [
         "new brand name",
         "ニューブランド"
       ],
       "subcategories": [
         "jacket", "pants", "shoes"
       ]
     }
   }
   ```
3. Commit and push
4. Railway will auto-redeploy
5. New brand will be scraped on next cycle

### To Adjust Frequency

Edit `pubert_scraper.py` line 300:
```python
schedule.every(30).minutes.do(self.run_pubert_cycle)  # Change 15 to 30
```

### To Create More Custom Scrapers

Clone the Pubert pattern:
1. Copy `pubert_scraper.py` → `[customer]_scraper.py`
2. Copy `pubert_brands.json` → `[customer]_brands.json`
3. Update channel name in scraper
4. Add to `channel_router.py`
5. Create Discord channel #[customer]
6. Deploy as separate Railway service

## 🎯 Summary

✅ **5 files added/modified**
✅ **Completely isolated** from main brand flow
✅ **Ready to deploy** to Railway
✅ **Full documentation** in PUBERT_SCRAPER_README.md

Just create the #pubert channel in Discord and deploy to Railway!
