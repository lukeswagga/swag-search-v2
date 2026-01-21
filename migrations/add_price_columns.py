"""
Migration script to add min_price and max_price columns to user_filters table

This migration:
- Adds min_price INTEGER column (default: 0 for existing rows)
- Adds max_price INTEGER column (default: 999999 for existing rows)
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


async def add_price_columns():
    """
    Add min_price and max_price columns to user_filters table
    """
    logger.info("🔧 Initializing database connection...")
    init_database()

    # Access session factory from database module
    if not hasattr(db_module, '_session_factory') or db_module._session_factory is None:
        raise ValueError("Database not initialized")

    logger.info("🔄 Starting migration: Adding price columns to user_filters")

    async with db_module._session_factory() as session:
        from sqlalchemy import text

        # Get database URL to determine type
        db_url = get_database_url() or ""
        is_postgres = "postgresql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()

        try:
            if is_postgres:
                logger.info("📊 Detected PostgreSQL database")

                # Check if user_filters table exists
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'user_filters'
                    )
                """))
                table_exists = result.scalar()

                if not table_exists:
                    logger.error("❌ user_filters table does not exist!")
                    logger.info("   Please create tables first using database.create_tables()")
                    return

                # Check if min_price column exists
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'user_filters'
                        AND column_name = 'min_price'
                    )
                """))
                min_price_exists = result.scalar()

                if min_price_exists:
                    logger.info("   ⏭️  min_price column already exists, skipping")
                else:
                    logger.info("   Adding min_price column...")
                    await session.execute(text("""
                        ALTER TABLE user_filters
                        ADD COLUMN min_price INTEGER
                    """))
                    # Set default value for existing rows
                    await session.execute(text("""
                        UPDATE user_filters
                        SET min_price = 0
                        WHERE min_price IS NULL
                    """))
                    await session.commit()
                    logger.info("   ✅ min_price column added (default: 0)")

                # Check if max_price column exists
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'user_filters'
                        AND column_name = 'max_price'
                    )
                """))
                max_price_exists = result.scalar()

                if max_price_exists:
                    logger.info("   ⏭️  max_price column already exists, skipping")
                else:
                    logger.info("   Adding max_price column...")
                    await session.execute(text("""
                        ALTER TABLE user_filters
                        ADD COLUMN max_price INTEGER
                    """))
                    # Set default value for existing rows
                    await session.execute(text("""
                        UPDATE user_filters
                        SET max_price = 999999
                        WHERE max_price IS NULL
                    """))
                    await session.commit()
                    logger.info("   ✅ max_price column added (default: 999999)")

                logger.info("✅ Migration complete!")

            elif is_sqlite:
                logger.info("📊 Detected SQLite database")

                # Check if user_filters table exists
                result = await session.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='user_filters'
                """))
                table_exists = result.fetchone() is not None

                if not table_exists:
                    logger.error("❌ user_filters table does not exist!")
                    logger.info("   Please create tables first using database.create_tables()")
                    return

                # For SQLite, check columns using PRAGMA
                result = await session.execute(text("PRAGMA table_info(user_filters)"))
                columns = [row[1] for row in result.fetchall()]

                min_price_exists = 'min_price' in columns
                max_price_exists = 'max_price' in columns

                if min_price_exists:
                    logger.info("   ⏭️  min_price column already exists, skipping")
                else:
                    logger.info("   Adding min_price column...")
                    await session.execute(text("""
                        ALTER TABLE user_filters
                        ADD COLUMN min_price INTEGER
                    """))
                    # Set default value for existing rows
                    await session.execute(text("""
                        UPDATE user_filters
                        SET min_price = 0
                        WHERE min_price IS NULL
                    """))
                    await session.commit()
                    logger.info("   ✅ min_price column added (default: 0)")

                if max_price_exists:
                    logger.info("   ⏭️  max_price column already exists, skipping")
                else:
                    logger.info("   Adding max_price column...")
                    await session.execute(text("""
                        ALTER TABLE user_filters
                        ADD COLUMN max_price INTEGER
                    """))
                    # Set default value for existing rows
                    await session.execute(text("""
                        UPDATE user_filters
                        SET max_price = 999999
                        WHERE max_price IS NULL
                    """))
                    await session.commit()
                    logger.info("   ✅ max_price column added (default: 999999)")

                logger.info("✅ Migration complete!")

            else:
                logger.warning("⚠️  Unknown database type")
                logger.info("   Please manually add columns:")
                logger.info("   ALTER TABLE user_filters ADD COLUMN min_price INTEGER;")
                logger.info("   ALTER TABLE user_filters ADD COLUMN max_price INTEGER;")
                logger.info("   UPDATE user_filters SET min_price = 0 WHERE min_price IS NULL;")
                logger.info("   UPDATE user_filters SET max_price = 999999 WHERE max_price IS NULL;")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Migration failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    try:
        asyncio.run(add_price_columns())
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)
