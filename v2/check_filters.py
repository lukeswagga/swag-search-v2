"""
Quick script to check user filters and verify Discord User IDs are set correctly
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
    from v2.database import init_database, get_active_filters
    from v2.config import get_database_url
except ImportError:
    from database import init_database, get_active_filters
    from config import get_database_url

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_filters():
    """Check all active user filters"""
    
    # Initialize database
    logger.info("🔧 Initializing database...")
    init_database()
    logger.info("✅ Database initialized")
    
    # Get all active filters
    filters = await get_active_filters()
    
    if not filters:
        print(f"\n{'='*60}")
        print("No active filters found in database")
        print(f"{'='*60}\n")
        print("To create test filters, run: python v2/create_test_filters.py")
        print("(But remember to update user_id fields with real Discord User IDs!)")
        return
    
    print(f"\n{'='*60}")
    print(f"Found {len(filters)} active filter(s)")
    print(f"{'='*60}\n")
    
    # Check for test user IDs
    test_user_ids = ["test_user_1", "test_user_2", "test_user_3"]
    has_test_ids = False
    
    for filter_obj in filters:
        user_id = filter_obj.user_id
        is_test_id = user_id in test_user_ids or not user_id.isdigit()
        
        if is_test_id:
            has_test_ids = True
        
        status = "⚠️  TEST ID" if is_test_id else "✅ Valid"
        
        print(f"{status} Filter ID: {filter_obj.id}")
        print(f"   User ID: {user_id}")
        print(f"   Name: {filter_obj.name}")
        print(f"   Active: {filter_obj.active}")
        print(f"   Brands: {filter_obj.brands or 'Any'}")
        print(f"   Price Range: ¥{filter_obj.price_min or 0:,} - ¥{filter_obj.price_max or '∞':,}")
        print(f"   Markets: {filter_obj.markets or 'Any'}")
        print()
    
    if has_test_ids:
        print(f"{'='*60}")
        print("⚠️  WARNING: Some filters use test user IDs!")
        print("   These filters won't receive DMs because they don't have real Discord User IDs.")
        print("   Update these filters with real Discord User IDs (numerical strings).")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}")
        print("✅ All filters have valid Discord User IDs!")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(check_filters())



