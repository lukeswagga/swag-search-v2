"""
Script to create test user filters for filter matching system
"""
import asyncio
import json
import logging
import sys
import os

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from models import UserFilter
    from database import init_database, create_tables, save_user_filter
    from config import get_database_url
except ImportError:
    from models import UserFilter
    from database import init_database, create_tables, save_user_filter
    from config import get_database_url

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_test_filters():
    """Create test user filters"""
    
    # Initialize database
    logger.info("🔧 Initializing database...")
    init_database()
    await create_tables()
    logger.info("✅ Database initialized")
    
    # Define test filters
    test_filters = [
        {
            "user_id": "test_user_1",
            "name": "Rick Owens Steals",
            "brands": ["rick owens"],
            "price_min": 0,
            "price_max": 50000,
            "markets": "yahoo,mercari",
            "keywords": []
        },
        {
            "user_id": "test_user_2",
            "name": "Raf Simons Any Price",
            "brands": ["raf simons"],
            "price_min": 0,
            "price_max": 999999,
            "markets": "yahoo,mercari",
            "keywords": []
        },
        {
            "user_id": "test_user_3",
            "name": "Budget Deals",
            "brands": ["rick owens", "raf simons", "comme des garcons"],
            "price_min": 0,
            "price_max": 20000,
            "markets": "yahoo,mercari",
            "keywords": []
        }
    ]
    
    created_count = 0
    
    for filter_data in test_filters:
        try:
            # Create UserFilter object
            user_filter = UserFilter(
                user_id=filter_data["user_id"],
                name=filter_data["name"],
                brands=json.dumps(filter_data["brands"]),  # Store as JSON string
                keywords=json.dumps(filter_data["keywords"]),  # Store as JSON string
                price_min=filter_data["price_min"],
                price_max=filter_data["price_max"],
                markets=filter_data["markets"],
                active=True
            )
            
            # Save to database
            filter_id = await save_user_filter(user_filter)
            created_count += 1
            
            logger.info(f"✅ Created filter #{filter_id}: {filter_data['name']} (user: {filter_data['user_id']})")
            print(f"  Filter ID: {filter_id}")
            print(f"  User ID: {filter_data['user_id']}")
            print(f"  Name: {filter_data['name']}")
            print(f"  Brands: {', '.join(filter_data['brands'])}")
            print(f"  Price Range: ¥{filter_data['price_min']:,} - ¥{filter_data['price_max']:,}")
            print(f"  Markets: {filter_data['markets']}")
            print(f"  Keywords: {filter_data['keywords'] if filter_data['keywords'] else 'None'}")
            print()
            
        except Exception as e:
            logger.error(f"❌ Failed to create filter '{filter_data['name']}': {e}", exc_info=True)
    
    print(f"{'='*60}")
    print(f"Created {created_count} test filters")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(create_test_filters())

