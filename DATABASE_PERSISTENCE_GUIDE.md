# Database Persistence Guide - Railway Deployment

## Problem Solved

**Issue**: After redeployment on Railway, scrapers were sending duplicate listings to Discord because the `seen_ids` tracking was getting reset.

**Root Cause**: The scrapers used JSON files (`seen_{scraper_name}.json`) to track seen auction IDs. On Railway, the filesystem is ephemeral—it gets wiped on every redeployment.

**Solution**: Migrated from JSON files to SQLite database with persistent storage.

## Implementation

### SQLite Database Structure

**Database File**: `auction_tracking.db`

**Table**: `seen_items`
```sql
CREATE TABLE seen_items (
    scraper_name TEXT NOT NULL,
    auction_id TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scraper_name, auction_id)
);

CREATE INDEX idx_scraper_name ON seen_items(scraper_name);
```

### How It Works

1. **Initialization** (core_scraper_base.py:87-113):
   - On startup, each scraper calls `init_database()` to create the table if it doesn't exist
   - Creates index for faster lookups

2. **Loading Seen IDs** (core_scraper_base.py:115-133):
   - Queries database for all auction IDs belonging to the scraper
   - Loads into memory as a set for fast duplicate checking

3. **Saving Seen IDs** (core_scraper_base.py:135-151):
   - Uses `INSERT OR IGNORE` to add new auction IDs
   - Only inserts IDs that don't already exist (prevents duplicates)
   - Commits after each scraping cycle

### Benefits

✅ **Persistent Across Deployments**: SQLite file persists on Railway with persistent volume
✅ **No Duplicates**: Database enforces uniqueness via PRIMARY KEY
✅ **Fast Lookups**: Index on `scraper_name` for efficient queries
✅ **Automatic Timestamps**: Tracks when each auction was first seen
✅ **Shared Database**: All scrapers use same database file, separate namespaces

## Railway Deployment Setup

### Required: Add Persistent Volume

To ensure the SQLite database persists across deployments:

1. **Go to Railway Project Settings**
2. **Navigate to "Volumes" tab**
3. **Click "Add Volume"**
4. **Configure Volume**:
   - **Mount Path**: `/app`
   - **Size**: 1GB (more than enough for database)
5. **Deploy**

### Verification

After deployment, check Railway logs for:
```
💾 Database initialized: auction_tracking.db
💾 Loaded X seen items from database
```

### Database Maintenance

The database is self-maintaining:
- Uses `INSERT OR IGNORE` to prevent duplicates
- Primary key constraint ensures data integrity
- Automatic cleanup in `cleanup_old_seen_ids()` keeps database size manageable

## Migration Notes

### From JSON to SQLite

No manual migration needed! On first run with new code:
1. SQLite database is created automatically
2. Existing JSON files are ignored (not deleted for safety)
3. Scrapers start tracking in the database going forward

### Database Location

- **Development**: `./auction_tracking.db` (local filesystem)
- **Production (Railway)**: `/app/auction_tracking.db` (persistent volume)

## Affected Scrapers

All scrapers now use persistent SQLite tracking:
- ✅ `new_listings_scraper.py`
- ✅ `buy_it_now_scraper.py`
- ✅ `ending_soon_scraper.py`
- ✅ `budget_steals_scraper.py`
- ✅ `pubert_scraper.py` (custom)
- ✅ `meyyjr_scraper.py` (custom)

## Troubleshooting

### Issue: Still seeing duplicates after redeployment

**Check**:
1. Verify persistent volume is mounted at `/app` in Railway settings
2. Check Railway logs for "💾 Database initialized" message
3. Verify database file exists: Check Railway shell with `ls -la auction_tracking.db`

### Issue: Database getting too large

**Solution**: The `cleanup_old_seen_ids()` method automatically trims the database:
- Keeps 20,000 most recent items when size > 30,000
- Keeps 10,000 most recent items when size > 50,000

You can also manually reset the database by deleting `auction_tracking.db` on Railway (via shell or volume management).

### Issue: SQLite errors

**Check**:
1. Verify Python `sqlite3` module is available (included in Python standard library)
2. Check file permissions on Railway volume
3. Review Railway logs for specific SQLite error messages

## Code Reference

### Key Files Modified
- `core_scraper_base.py` - Added SQLite implementation (lines 87-151)
- All scraper files inherit the new database-backed tracking

### Migration from JSON (if needed)

If you want to preserve existing seen IDs from JSON files:

```python
import json
import sqlite3

# Load from JSON
with open('seen_new_listings_scraper.json', 'r') as f:
    seen_ids = set(json.load(f))

# Save to SQLite
conn = sqlite3.connect('auction_tracking.db')
cursor = conn.cursor()
for auction_id in seen_ids:
    cursor.execute('''
        INSERT OR IGNORE INTO seen_items (scraper_name, auction_id)
        VALUES (?, ?)
    ''', ('new_listings_scraper', auction_id))
conn.commit()
conn.close()
```

## Performance

### Database Size Estimates
- Each auction ID entry: ~100 bytes
- 10,000 entries: ~1 MB
- 100,000 entries: ~10 MB
- 1 million entries: ~100 MB

### Query Performance
- Indexed lookups: O(log n)
- In-memory duplicate check: O(1)
- Insert performance: 1000s of inserts per second

## Summary

The migration from JSON files to SQLite database ensures that **scrapers will no longer send duplicate listings after redeployment**. The database persists across Railway deployments when using a persistent volume, providing reliable duplicate detection indefinitely.

**User Impact**: Clients like Pubert and Meyyjr will no longer experience spam after redeployments! 🎉
