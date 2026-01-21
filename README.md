# Swag Search v2 - New Architecture

This directory contains the new v2 architecture for Swag Search, built with async SQLAlchemy for better performance and scalability.

## Overview

v2 introduces:
- **Async SQLAlchemy** with asyncpg for PostgreSQL (or aiosqlite for SQLite)
- **User-centric filtering** - each user can define custom filters
- **Improved data model** - better tracking of listings and alerts
- **Scalable architecture** - ready for multi-user, multi-market support

## Structure

```
v2/
├── models.py              # SQLAlchemy async models
├── test_models.py         # Test file to verify models work
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── ARCHITECTURE_ANALYSIS.md  # Analysis of current system
```

## Models

### 1. `UserFilter`
User-defined filters for personalized auction alerts.

**Fields:**
- `id`: Primary key
- `user_id`: Discord user ID
- `name`: Filter name (e.g., "Budget Finds Under $100")
- `markets`: Comma-separated markets (e.g., "yahoo,mercari")
- `brands`: JSON array of brand names
- `keywords`: JSON array of search keywords
- `price_min`, `price_max`: Price range filter
- `listing_types`: Comma-separated types (e.g., "auction,buy_it_now")
- `active`: Whether filter is active
- `created_at`, `updated_at`: Timestamps

### 2. `Listing`
Auction listings from various markets.

**Fields:**
- `id`: Primary key
- `market`: Source market (e.g., "yahoo", "mercari")
- `external_id`: Auction ID from source platform
- `title`: Listing title
- `price_jpy`: Price in Japanese Yen
- `brand`: Detected brand name
- `url`: Listing URL
- `image_url`: Thumbnail image URL
- `listing_type`: Type of listing (auction, buy_it_now, etc.)
- `seller_id`: Seller identifier
- `first_seen`, `last_seen`: Timestamps for tracking

**Indexes:**
- Unique: `(market, external_id)` - prevents duplicate listings
- Indexed: `brand`, `price_jpy`, `first_seen`

### 3. `AlertSent`
Tracks which users have been notified about which listings.

**Fields:**
- `id`: Primary key
- `listing_id`: Foreign key to `listings`
- `user_id`: Discord user ID
- `filter_id`: Foreign key to `user_filters` (optional - can be manual alert)
- `sent_at`: When the alert was sent

**Indexes:**
- Unique: `(user_id, listing_id)` - prevents duplicate alerts
- Indexed: `sent_at` for time-based queries

## Setup

### Install Dependencies

```bash
cd v2
pip install -r requirements.txt
```

### For PostgreSQL (Production)
```bash
# Requires asyncpg
pip install asyncpg
```

### For SQLite (Testing/Local)
```bash
# Requires aiosqlite
pip install aiosqlite
```

## Testing

Run the test file to verify models work:

```bash
python test_models.py
```

This will:
1. Create a SQLite test database
2. Create all tables
3. Test CRUD operations
4. Test relationships
5. Verify unique constraints
6. Clean up test database

**Expected Output:**
```
🧪 Testing v2 SQLAlchemy Models with SQLite
============================================================
🔧 Initializing database: sqlite+aiosqlite:///test_v2.db
📦 Creating tables...
✅ Tables created successfully
...
✅ ALL TESTS PASSED!
```

## Usage Example

```python
import asyncio
from models import init_database, create_tables, AsyncSessionLocal, UserFilter, Listing

# Initialize database (PostgreSQL)
init_database("postgresql+asyncpg://user:pass@localhost/dbname")

# Or SQLite for testing
init_database("sqlite+aiosqlite:///app.db")

# Create tables
asyncio.run(create_tables())

# Use in async function
async def example():
    async with AsyncSessionLocal() as session:
        # Create a user filter
        user_filter = UserFilter(
            user_id=12345,
            name="Raf Simons Finds",
            markets="yahoo",
            brands='["Raf Simons"]',
            price_max=200.0,
            active=True
        )
        session.add(user_filter)
        await session.commit()
        
        # Query filters
        from sqlalchemy import select
        result = await session.execute(
            select(UserFilter).where(UserFilter.user_id == 12345)
        )
        filters = result.scalars().all()
        print(f"Found {len(filters)} filters")

asyncio.run(example())
```

## Database URLs

### PostgreSQL (Production)
```
postgresql+asyncpg://username:password@host:port/database
```

### SQLite (Testing)
```
sqlite+aiosqlite:///path/to/database.db
```

## Next Steps

1. ✅ Models created
2. ⏳ Create async scraper services
3. ⏳ Implement user filter matching logic
4. ⏳ Build alert dispatch system
5. ⏳ Migration script from v1 to v2

## Differences from v1

| Feature | v1 | v2 |
|---------|----|----|
| Database | Sync (psycopg2/sqlite3) | Async (asyncpg/aiosqlite) |
| Filtering | Global (scraper-level) | Per-user filters |
| Listing Tracking | `seen_items` table | `listings` table with relationships |
| Alert Tracking | None | `alerts_sent` table |
| Brand Matching | Simple substring | TBD - fuzzy matching planned |
| Scalability | Limited by rate limiting | Designed for multi-user |

