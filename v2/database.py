"""
Async database operations for v2 scrapers.
Uses SQLAlchemy async with asyncpg (PostgreSQL) or aiosqlite (SQLite for testing).

This module provides persistent storage and deduplication for listings across scraper cycles.
"""
import logging
import os
from typing import List, Optional, Dict
from datetime import datetime, timezone
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Import models
try:
    from .models import Base, Listing
except ImportError:
    from models import Base, Listing

# Global engine and session factory (will be initialized by init_database)
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def init_database(database_url: Optional[str] = None) -> None:
    """
    Initialize async database connection and create tables.
    
    Args:
        database_url: Database URL (e.g., postgresql+asyncpg://user:pass@host/db)
                     For SQLite: sqlite+aiosqlite:///./test.db
                     If None, uses models.py's init_database function
    """
    global _engine, _session_factory
    
    if database_url is None:
        # Use the existing models.py initialization
        from config import get_database_url
        database_url = get_database_url()
        
        if not database_url:
            # Default to SQLite for local testing (relative to current working directory)
            # Use absolute path to avoid directory issues
            db_path = os.path.abspath("./test.db")
            database_url = f"sqlite+aiosqlite:///{db_path}"
            logger.warning(f"⚠️  No DATABASE_URL found in environment, using SQLite: {database_url}")
        else:
            logger.info(f"✅ Using database URL from environment")
    
    # Convert postgresql:// to postgresql+asyncpg:// if needed
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        logger.info(f"   Converted to asyncpg URL: {database_url.split('@')[0]}@...")
    
    # Convert sqlite:// to sqlite+aiosqlite:// if needed
    if database_url.startswith("sqlite:///") and "+aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        logger.info(f"   Converted to aiosqlite URL")
    
    logger.info(f"🔧 Initializing database connection...")
    
    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        future=True,
        # SQLite-specific settings
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
    )
    
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    logger.info("✅ Database connection initialized")


async def create_tables() -> None:
    """Create all tables if they don't exist"""
    if _engine is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")


async def drop_tables() -> None:
    """Drop all tables (use with caution!)"""
    if _engine is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("✅ Database tables dropped")


async def listing_exists(external_id: str, market: str) -> bool:
    """
    Check if a listing with the given external_id and market already exists in the database.
    
    Args:
        external_id: External ID of the listing (auction ID, item ID, etc.)
        market: Market name (e.g., "yahoo", "mercari")
    
    Returns:
        True if listing exists, False otherwise
    
    Notes:
        This function is async to support database queries. For backward compatibility
        with existing code, it can be called without await if using an in-memory cache
        (not recommended for production).
    """
    if not external_id or not market:
        return False
    
    if _session_factory is None:
        # Database not initialized - return False (no listings exist)
        logger.debug(f"Database not initialized, listing_exists({external_id}, {market}) = False")
        return False
    
    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(Listing).where(
                    and_(
                        Listing.external_id == external_id,
                        Listing.market == market
                    )
                )
            )
            listing = result.scalar_one_or_none()
            exists = listing is not None
            if exists:
                logger.debug(f"listing_exists: {market}:{external_id} already exists in database")
            return exists
    except Exception as e:
        logger.error(f"❌ Error checking listing existence: {e}", exc_info=True)
        return False


async def save_listing(listing: Listing) -> bool:
    """
    Save a single listing to the database.
    If the listing already exists (by market+external_id), update last_seen timestamp.
    
    Args:
        listing: Listing object to save
    
    Returns:
        True if listing was saved (new), False if it was already a duplicate
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        async with _session_factory() as session:
            # Check if listing already exists
            result = await session.execute(
                select(Listing).where(
                    and_(
                        Listing.external_id == listing.external_id,
                        Listing.market == listing.market
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update last_seen timestamp
                await session.execute(
                    update(Listing)
                    .where(Listing.id == existing.id)
                    .values(last_seen=datetime.now(timezone.utc))
                )
                await session.commit()
                logger.debug(f"Updated existing listing: {listing.market}:{listing.external_id}")
                return False  # Duplicate
            else:
                # Insert new listing
                session.add(listing)
                await session.commit()
                logger.debug(f"Saved new listing: {listing.market}:{listing.external_id}")
                return True  # New listing
                
    except Exception as e:
        logger.error(f"❌ Error saving listing: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        return False


async def save_listings_batch(listings: List[Listing]) -> Dict[str, int]:
    """
    Save multiple listings to the database in a batch.
    Uses PostgreSQL's ON CONFLICT for efficient upserts.
    
    Args:
        listings: List of Listing objects to save
    
    Returns:
        Dictionary with stats:
        - saved: Number of new listings saved
        - duplicates: Number of duplicates (existing listings)
        - errors: Number of errors
        - total: Total listings processed
    """
    if not listings:
        return {"saved": 0, "duplicates": 0, "errors": 0, "total": 0}
    
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    stats = {"saved": 0, "duplicates": 0, "errors": 0, "total": len(listings)}
    
    try:
        async with _session_factory() as session:
            # Build lookup map: (market, external_id) -> listing
            lookup_map = {(listing.market, listing.external_id): listing for listing in listings}
            
            # Single bulk query to check which listings exist
            # Use OR conditions - PostgreSQL handles this efficiently with indexes
            if lookup_map:
                from sqlalchemy import or_
                conditions = [
                    and_(Listing.market == market, Listing.external_id == external_id)
                    for market, external_id in lookup_map.keys()
                ]
                
                result = await session.execute(
                    select(Listing.market, Listing.external_id, Listing.id).where(
                        or_(*conditions)
                    )
                )
                # Build map of existing listings: (market, external_id) -> id
                existing_map = {(row[0], row[1]): row[2] for row in result.fetchall()}
            else:
                existing_map = {}
            
            # Separate new and existing listings
            new_listings = []
            existing_ids_to_update = []
            now = datetime.now(timezone.utc)
            
            for (market, external_id), listing in lookup_map.items():
                if (market, external_id) in existing_map:
                    existing_ids_to_update.append(existing_map[(market, external_id)])
                    stats["duplicates"] += 1
                else:
                    new_listings.append(listing)
                    stats["saved"] += 1
            
            # Bulk insert new listings
            if new_listings:
                session.add_all(new_listings)
            
            # Bulk update existing listings' last_seen timestamp
            if existing_ids_to_update:
                await session.execute(
                    update(Listing)
                    .where(Listing.id.in_(existing_ids_to_update))
                    .values(last_seen=now)
                )
            
            # Commit all changes at once
            await session.commit()
            logger.info(
                f"💾 Batch save complete: {stats['saved']} new, "
                f"{stats['duplicates']} duplicates, {stats['errors']} errors"
            )
            
    except Exception as e:
        logger.error(f"❌ Error in batch save: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        stats["errors"] = stats["total"]
    
    return stats


async def get_listings_since(timestamp: datetime) -> List[Listing]:
    """
    Get all listings that were first_seen after the given timestamp.
    
    Args:
        timestamp: Get listings first_seen after this time
    
    Returns:
        List of Listing objects
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(Listing).where(Listing.first_seen >= timestamp)
                .order_by(Listing.first_seen.desc())
            )
            listings = result.scalars().all()
            logger.debug(f"Found {len(listings)} listings since {timestamp}")
            return list(listings)
    except Exception as e:
        logger.error(f"❌ Error querying listings: {e}", exc_info=True)
        return []


async def close_database() -> None:
    """
    Close database connections and clean up resources.
    Call this when shutting down the application.
    """
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("✅ Database connections closed")
    else:
        logger.debug("Database already closed or never initialized")


# Backward compatibility: synchronous wrapper for listing_exists
# Note: This only works if database is initialized and will log a warning
# For new code, use await listing_exists() directly
def listing_exists_sync(external_id: str, market: str) -> bool:
    """
    Synchronous wrapper for listing_exists (for backward compatibility).
    ⚠️  WARNING: This is not truly async-safe. Use async listing_exists() in new code.
    
    For now, this returns False if database isn't ready, which is safe for
    the smart pagination use case (assumes listings don't exist until proven otherwise).
    """
    if _session_factory is None:
        return False
    
    # Create a new event loop or use existing one
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run() in a running loop - return False (safe default)
            logger.warning(
                f"⚠️  listing_exists_sync called in async context - use await listing_exists() instead"
            )
            return False
        else:
            return loop.run_until_complete(listing_exists(external_id, market))
    except RuntimeError:
        # No event loop - create one
        return asyncio.run(listing_exists(external_id, market))
