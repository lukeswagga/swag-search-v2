# Railway Quick Setup Guide - Fix Duplicates Forever

## Problem
- ❌ Pubert channel getting spammed with duplicates after every Railway redeploy
- ❌ Railway filesystem is ephemeral (resets on deploy)
- ❌ Your Railway plan doesn't have "Volumes" tab

## Solution
Use **Railway PostgreSQL** instead of filesystem storage!

---

## Step-by-Step Setup (5 minutes)

### 1. Add PostgreSQL to Railway

1. **Go to Railway Dashboard**: https://railway.app
2. **Select your project** (yahoo-japan-scraper)
3. **Click the "+ New" button** (top right)
4. **Select "Database"** from dropdown
5. **Click "Add PostgreSQL"**
6. ✅ Done! Railway automatically:
   - Creates a PostgreSQL database
   - Sets `DATABASE_URL` environment variable
   - Handles backups automatically

### 2. Redeploy All Scrapers

You need to redeploy each scraper service. For each one:

1. Go to the service (e.g., `pubert_scraper`)
2. Click **"Settings"** tab
3. Click **"Redeploy"** button
4. Repeat for all scrapers:
   - ☑️ `pubert_scraper`
   - ☑️ `meyyjr_scraper`
   - ☑️ `new_listings_scraper`
   - ☑️ `buy_it_now_scraper`
   - ☑️ `ending_soon_scraper`
   - ☑️ `budget_steals_scraper`

### 3. Verify It's Working

After each scraper redeploys, **check the Railway logs**:

**Good Signs** ✅:
```
🐘 PostgreSQL adapter loaded
💾 Using PostgreSQL database (Railway) for persistent tracking
💾 Database initialized (PostgreSQL)
💾 Loaded 0 seen items from database  (first time will be 0)
👔 Category filter: Men's Fashion (2084005009)
```

**Bad Signs** ❌:
```
⚠️ DATABASE_URL set but psycopg2 not installed
💾 Using SQLite database for persistent tracking  (means Postgres not detected)
```

If you see bad signs:
- Make sure you added PostgreSQL database
- Check that DATABASE_URL is set in environment variables
- Redeploy again

### 4. Test for Duplicates

1. **Wait for first scraping cycle** (15 minutes for Pubert/Meyyjr)
2. **Note the listings** posted to Discord
3. **Manually trigger a redeploy** of the scraper
4. **Wait for next cycle**
5. ✅ **Should NOT see duplicates!**

Old behavior ❌:
```
[Redeploy happens]
→ Same 50 listings sent again (spam!)
```

New behavior ✅:
```
[Redeploy happens]
→ Only NEW listings sent (no duplicates!)
```

---

## What Changed Automatically

The code now **auto-detects** which database to use:

- **On Railway** (with PostgreSQL addon): Uses PostgreSQL
- **Locally** (no DATABASE_URL): Uses SQLite

No code changes needed in your scraper files! 🎉

---

## Benefits

✅ **No more duplicate spam** to Pubert/Meyyjr after redeploys
✅ **Works on ALL Railway plans** (no Volumes needed)
✅ **Automatic backups** by Railway
✅ **Better performance** than SQLite for production
✅ **Shared database** - all scrapers use same Postgres instance

---

## Cost

Railway PostgreSQL addon:
- **Free tier**: 500 MB storage, 100 hours runtime/month
- **More than enough** for auction ID tracking (uses ~1 MB per 10,000 items)
- Database will handle millions of auction IDs before hitting limits

---

## Troubleshooting

### Issue: Still seeing duplicates after setup

**Check:**
1. PostgreSQL addon is added (see it in Railway project)
2. `DATABASE_URL` environment variable is set (check Settings → Variables)
3. Logs show "Using PostgreSQL database (Railway)" not "Using SQLite"
4. All scrapers have been redeployed AFTER adding Postgres

### Issue: Error connecting to database

**Solution:**
Check Railway logs for specific error. Common issues:
- Postgres addon still starting up (wait 2-3 minutes)
- Incorrect DATABASE_URL format (Railway sets this automatically, don't modify it)

### Issue: Can't find "+ New" button

**Solution:**
- Make sure you're on the **project dashboard**, not inside a service
- Should see all your services (pubert_scraper, meyyjr_scraper, etc.)
- "+ New" button is in the top right

---

## Rollback (if needed)

If PostgreSQL has issues, you can rollback:

1. **Remove PostgreSQL addon** from Railway
2. **Remove DATABASE_URL** environment variable
3. **Redeploy scrapers**
4. Will fall back to SQLite (but duplicates will occur on redeploy without Volumes)

---

## Summary

**Before:**
- Filesystem storage → wiped on deploy → duplicates sent

**After:**
- PostgreSQL storage → persists forever → no duplicates! 🎉

**Setup Time:** ~5 minutes
**Difficulty:** Easy (just click buttons in Railway dashboard)
**Result:** Never spam your clients with duplicates again!
