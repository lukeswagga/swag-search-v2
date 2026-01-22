"""
Database migration: Add indexes for search performance.

This migration adds indexes to optimize the new search endpoints:
- Case-insensitive brand search
- Price filtering
- Time-based queries
- Market filtering
- Composite index for common query patterns
"""

import asyncio
import logging
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_indexes():
    """Add performance indexes to the listings table"""
    from database import init_database, _engine
    from config import get_database_url

    # Initialize database
    db_url = get_database_url()
    if not db_url:
        logger.error("❌ DATABASE_URL not found")
        return

    init_database(db_url)

    if _engine is None:
        logger.error("❌ Failed to initialize database engine")
        return

    logger.info("🔧 Adding search performance indexes...")

    # List of indexes to create
    indexes = [
        # Case-insensitive brand search (PostgreSQL-specific with LOWER function)
        {
            "name": "idx_listings_brand_lower",
            "sql": "CREATE INDEX IF NOT EXISTS idx_listings_brand_lower ON listings (LOWER(brand))",
            "description": "Case-insensitive brand search"
        },
        # Market filtering (if not already exists)
        {
            "name": "idx_listings_market",
            "sql": "CREATE INDEX IF NOT EXISTS idx_listings_market ON listings (market)",
            "description": "Market filtering"
        },
        # Price filtering (if not already exists - should exist from model definition)
        {
            "name": "idx_listings_price_jpy_only",
            "sql": "CREATE INDEX IF NOT EXISTS idx_listings_price_jpy_only ON listings (price_jpy)",
            "description": "Price range filtering"
        },
        # Composite index for common query pattern: brand + price + time
        {
            "name": "idx_listings_brand_price_time",
            "sql": "CREATE INDEX IF NOT EXISTS idx_listings_brand_price_time ON listings (LOWER(brand), price_jpy, first_seen DESC)",
            "description": "Composite index for brand+price+time queries"
        },
        # Time-based DESC index for recent listings
        {
            "name": "idx_listings_first_seen_desc",
            "sql": "CREATE INDEX IF NOT EXISTS idx_listings_first_seen_desc ON listings (first_seen DESC)",
            "description": "Time-based queries (newest first)"
        }
    ]

    # Create indexes
    async with _engine.begin() as conn:
        for index in indexes:
            try:
                logger.info(f"   Creating {index['name']}: {index['description']}")
                await conn.execute(text(index['sql']))
                logger.info(f"   ✅ {index['name']} created")
            except Exception as e:
                # Check if it's just because the index already exists
                if "already exists" in str(e).lower():
                    logger.info(f"   ℹ️  {index['name']} already exists")
                else:
                    logger.error(f"   ❌ Error creating {index['name']}: {e}")

    logger.info("✅ Index migration complete!")

    # Close database connection
    from database import close_database
    await close_database()


async def verify_indexes():
    """Verify that indexes were created successfully"""
    from database import init_database, _engine
    from config import get_database_url

    # Initialize database
    db_url = get_database_url()
    if not db_url:
        logger.error("❌ DATABASE_URL not found")
        return

    init_database(db_url)

    if _engine is None:
        logger.error("❌ Failed to initialize database engine")
        return

    logger.info("\n📊 Verifying indexes on listings table...")

    async with _engine.connect() as conn:
        # Query to get all indexes on listings table (PostgreSQL-specific)
        result = await conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'listings'
            ORDER BY indexname;
        """))

        indexes = result.fetchall()

        if indexes:
            logger.info(f"\n   Found {len(indexes)} indexes:")
            for idx_name, idx_def in indexes:
                logger.info(f"   - {idx_name}")
        else:
            logger.warning("   No indexes found on listings table")

    # Close database connection
    from database import close_database
    await close_database()


if __name__ == "__main__":
    print("=" * 60)
    print("SwagSearch Search Performance Index Migration")
    print("=" * 60)
    print()

    # Run migration
    asyncio.run(add_indexes())

    print()
    print("=" * 60)

    # Verify indexes
    try:
        asyncio.run(verify_indexes())
    except Exception as e:
        logger.warning(f"Could not verify indexes (may be using SQLite): {e}")

    print()
    print("Migration complete!")
    print("=" * 60)
