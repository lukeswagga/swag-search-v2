"""
Migration script to change user_id from integer to string in user_filters and alerts_sent tables
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


async def migrate_user_id_to_string():
    """
    Migrate user_id columns from integer to varchar(100)
    """
    logger.info("🔧 Initializing database connection...")
    init_database()
    
    # Access session factory from database module
    if not hasattr(db_module, '_session_factory') or db_module._session_factory is None:
        raise ValueError("Database not initialized")
    
    logger.info("🔄 Starting migration: user_id integer -> varchar(100)")
    
    async with db_module._session_factory() as session:
        # Check database type (PostgreSQL vs SQLite)
        from sqlalchemy import text
        
        # Get database URL to determine type
        db_url = get_database_url() or ""
        is_postgres = "postgresql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()
        
        if is_postgres:
            logger.info("📊 Detected PostgreSQL database")
            
            try:
                # Check if user_filters table exists and column type
                result = await session.execute(text("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_filters' 
                    AND column_name = 'user_id'
                """))
                row = result.fetchone()
                
                if row:
                    current_type = row[0]
                    logger.info(f"   Current user_id type in user_filters: {current_type}")
                    
                    if current_type == 'integer':
                        logger.info("   Migrating user_filters.user_id...")
                        # Convert existing integer user_ids to strings
                        await session.execute(text("""
                            ALTER TABLE user_filters 
                            ALTER COLUMN user_id TYPE VARCHAR(100) USING user_id::text
                        """))
                        await session.commit()
                        logger.info("   ✅ user_filters.user_id migrated")
                    else:
                        logger.info(f"   ⏭️  user_filters.user_id already {current_type}, skipping")
                else:
                    logger.warning("   ⚠️  user_filters table or user_id column not found")
                
                # Check alerts_sent table
                result = await session.execute(text("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'alerts_sent' 
                    AND column_name = 'user_id'
                """))
                row = result.fetchone()
                
                if row:
                    current_type = row[0]
                    logger.info(f"   Current user_id type in alerts_sent: {current_type}")
                    
                    if current_type == 'integer':
                        logger.info("   Migrating alerts_sent.user_id...")
                        # Convert existing integer user_ids to strings
                        await session.execute(text("""
                            ALTER TABLE alerts_sent 
                            ALTER COLUMN user_id TYPE VARCHAR(100) USING user_id::text
                        """))
                        await session.commit()
                        logger.info("   ✅ alerts_sent.user_id migrated")
                    else:
                        logger.info(f"   ⏭️  alerts_sent.user_id already {current_type}, skipping")
                else:
                    logger.warning("   ⚠️  alerts_sent table or user_id column not found")
                
                logger.info("✅ Migration complete!")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Migration failed: {e}", exc_info=True)
                raise
                
        elif is_sqlite:
            logger.info("📊 Detected SQLite database")
            logger.info("   SQLite doesn't support ALTER COLUMN TYPE directly")
            logger.info("   Recommendation: Drop and recreate tables with new schema")
            logger.info("   (This will delete existing data)")
            
            response = input("   Drop and recreate tables? (yes/no): ")
            if response.lower() == 'yes':
                from database import drop_tables, create_tables
                logger.info("   Dropping tables...")
                await drop_tables()
                logger.info("   Creating tables with new schema...")
                await create_tables()
                logger.info("   ✅ Tables recreated with new schema")
            else:
                logger.info("   ⏭️  Migration cancelled")
                
        else:
            logger.warning("⚠️  Unknown database type, cannot migrate automatically")
            logger.info("   Please manually alter columns:")
            logger.info("   ALTER TABLE user_filters ALTER COLUMN user_id TYPE VARCHAR(100);")
            logger.info("   ALTER TABLE alerts_sent ALTER COLUMN user_id TYPE VARCHAR(100);")


if __name__ == "__main__":
    try:
        asyncio.run(migrate_user_id_to_string())
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)
