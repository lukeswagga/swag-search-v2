# PostgreSQL Migration Guide - Railway Deployment

## Why PostgreSQL Instead of SQLite?

Railway's filesystem is ephemeral (resets on deploy). While Railway Volumes would solve this, they're not available on all plans. **PostgreSQL is a better solution** because:

✅ **Built-in to Railway** - Free database addon
✅ **Automatic backups** - Railway handles it
✅ **Better for production** - More robust than SQLite
✅ **No volume management needed**

## Quick Migration Steps

### 1. Add PostgreSQL to Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically create a PostgreSQL database and set `DATABASE_URL` environment variable

### 2. Install PostgreSQL Adapter

Add to `requirements.txt`:
```
psycopg2-binary
```

### 3. Update Core Scraper Base

I'll create a new version that auto-detects PostgreSQL vs SQLite:

**Modified `core_scraper_base.py`** - detects `DATABASE_URL` and uses PostgreSQL if available, falls back to SQLite locally.

## Code Changes Needed

See `core_scraper_base_postgres.py` for the updated implementation.

### Key Changes:
- Uses `DATABASE_URL` environment variable (Railway sets this automatically)
- Falls back to SQLite for local development
- Same API - no changes needed in scraper files!

## Deployment

1. **Add PostgreSQL to Railway** (steps above)
2. **Update `requirements.txt`**:
   ```bash
   git add requirements.txt
   git commit -m "Add psycopg2 for PostgreSQL support"
   git push
   ```
3. **Deploy** - Railway will automatically use PostgreSQL

## Testing

After deployment, check Railway logs for:
```
💾 Using PostgreSQL database (Railway)
💾 Database initialized (PostgreSQL)
💾 Loaded X seen items from database
```

## Rollback to SQLite (if needed)

If PostgreSQL has issues, simply remove the `DATABASE_URL` environment variable and it will fall back to SQLite (though duplicates will occur on redeploy without volumes).
