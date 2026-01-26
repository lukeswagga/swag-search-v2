import asyncio
import os
from datetime import datetime, timedelta, timezone
from database import init_database, _session_factory
from models import Listing
from sqlalchemy import select, func, delete
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_old_listings():
    """
    Remove old listings to prevent database from growing infinitely.
    Strategy: Keep last 7 days OR 50,000 items, whichever is more.
    """
    try:
        # Initialize database if not already initialized
        if _session_factory is None:
            from config import get_database_url
            db_url = get_database_url()
            if not db_url:
                raise ValueError("DATABASE_URL not set")
            init_database(db_url)
        
        async with _session_factory() as session:
            # Count total listings
            count_query = select(func.count(Listing.id))
            result = await session.execute(count_query)
            total_count = result.scalar()
            
            logger.info(f"📊 Total listings in database: {total_count}")
            
            # Calculate cutoff date (7 days ago)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Strategy 1: If > 50,000 items, delete oldest beyond 50k limit
            if total_count > 50000:
                # Get the 50,000th newest item's timestamp
                query = (
                    select(Listing.first_seen)
                    .order_by(Listing.first_seen.desc())
                    .offset(50000)
                    .limit(1)
                )
                result = await session.execute(query)
                keep_cutoff = result.scalar()
                
                if keep_cutoff:
                    # Delete everything older than the 50,000th item
                    delete_query = delete(Listing).where(Listing.first_seen < keep_cutoff)
                    result = await session.execute(delete_query)
                    await session.commit()
                    
                    logger.info(f"🗑️  Deleted {result.rowcount} listings (keeping newest 50,000)")
                    return result.rowcount
                else:
                    # Fallback: shouldn't happen, but if it does, use 7-day strategy
                    logger.warning("⚠️  Could not determine 50k cutoff, falling back to 7-day cleanup")
            
            # Strategy 2: Delete items older than 7 days
            delete_query = delete(Listing).where(Listing.first_seen < cutoff_date)
            result = await session.execute(delete_query)
            await session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"🗑️  Deleted {deleted_count} listings older than 7 days")
            return deleted_count
                
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        raise

async def main():
    logger.info("🧹 Starting database cleanup...")
    deleted = await cleanup_old_listings()
    logger.info(f"✅ Cleanup complete. Removed {deleted} old listings")

if __name__ == "__main__":
    asyncio.run(main())

