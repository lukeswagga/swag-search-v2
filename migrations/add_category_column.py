"""
Migration script to add category column to listings table

This migration:
- Adds category VARCHAR(200) column (nullable) to listings table
- Is idempotent (safe to run multiple times)
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from database import init_database
    from config import get_database_url
    import database as db_module
except ImportError:
    from database import init_database
    from config import get_database_url
    import database as db_module

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def add_category_column():
    """
    Add category column to listings table
    """
    logger.info("🔧 Initializing database connection...")
    init_database()

    # Access session factory from database module
    if not hasattr(db_module, '_session_factory') or db_module._session_factory is None:
        raise ValueError("Database not initialized")

    logger.info("🔄 Starting migration: Adding category column to listings")

    async with db_module._session_factory() as session:
        from sqlalchemy import text

        # Get database URL to determine type
        db_url = get_database_url() or ""
        is_postgres = "postgresql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()

        try:
            if is_postgres:
                logger.info("📊 Detected PostgreSQL database")

                # Check if listings table exists
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'listings'
                    )
                """))
                table_exists = result.scalar()

                if not table_exists:
                    logger.error("❌ listings table does not exist!")
                    logger.info("   Please create tables first using database.create_tables()")
                    return

                # Check if category column exists
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'listings'
                        AND column_name = 'category'
                    )
                """))
                category_exists = result.scalar()

                if category_exists:
                    logger.info("   ⏭️  category column already exists, skipping")
                else:
                    logger.info("   Adding category column...")
                    await session.execute(text("""
                        ALTER TABLE listings
                        ADD COLUMN category VARCHAR(200)
                    """))
                    await session.commit()
                    logger.info("   ✅ category column added")

                logger.info("✅ Migration complete!")

            elif is_sqlite:
                logger.info("📊 Detected SQLite database")

                # Check if listings table exists
                result = await session.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='listings'
                """))
                table_exists = result.fetchone() is not None

                if not table_exists:
                    logger.error("❌ listings table does not exist!")
                    logger.info("   Please create tables first using database.create_tables()")
                    return

                # For SQLite, check columns using PRAGMA
                result = await session.execute(text("PRAGMA table_info(listings)"))
                columns = [row[1] for row in result.fetchall()]

                category_exists = 'category' in columns

                if category_exists:
                    logger.info("   ⏭️  category column already exists, skipping")
                else:
                    logger.info("   Adding category column...")
                    await session.execute(text("""
                        ALTER TABLE listings
                        ADD COLUMN category VARCHAR(200)
                    """))
                    await session.commit()
                    logger.info("   ✅ category column added")

                logger.info("✅ Migration complete!")

            else:
                logger.warning("⚠️  Unknown database type")
                logger.info("   Please manually add column:")
                logger.info("   ALTER TABLE listings ADD COLUMN category VARCHAR(200);")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Migration failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    try:
        asyncio.run(add_category_column())
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)

