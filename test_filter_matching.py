"""
Test script for filter matching system
- Creates test filters
- Runs one scraper cycle
- Shows which listings matched which filters
- Shows how many alerts would be sent per user
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from collections import defaultdict

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from scrapers.yahoo_scraper import YahooScraper
    from scrapers.mercari_api_scraper import MercariAPIScraper
    from models import UserFilter, Listing
    from database import init_database, create_tables, save_listings_batch, get_active_filters, was_alert_sent, save_user_filter, get_listings_since
    from filter_matcher import FilterMatcher
    from config import get_database_url
    import database as db_module
except ImportError:
    from scrapers.yahoo_scraper import YahooScraper
    from scrapers.mercari_api_scraper import MercariAPIScraper
    from models import UserFilter, Listing
    from database import init_database, create_tables, save_listings_batch, get_active_filters, was_alert_sent, save_user_filter, get_listings_since
    from filter_matcher import FilterMatcher
    from config import get_database_url
    import database as db_module

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_test_filters():
    """Create test user filters"""
    import json
    
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
            user_filter = UserFilter(
                user_id=filter_data["user_id"],
                name=filter_data["name"],
                brands=json.dumps(filter_data["brands"]),
                keywords=json.dumps(filter_data["keywords"]),
                price_min=filter_data["price_min"],
                price_max=filter_data["price_max"],
                markets=filter_data["markets"],
                active=True
            )
            
            filter_id = await save_user_filter(user_filter)
            created_count += 1
            
            logger.info(f"✅ Created filter #{filter_id}: {filter_data['name']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create filter '{filter_data['name']}': {e}", exc_info=True)
    
    return created_count


async def run_test():
    """Run filter matching test"""
    
    print(f"\n{'='*60}")
    print("Filter Matching Test")
    print(f"{'='*60}\n")
    
    # Step 1: Initialize database
    logger.info("🔧 Step 1: Initializing database...")
    init_database()
    await create_tables()
    logger.info("✅ Database initialized\n")
    
    # Step 2: Create test filters
    logger.info("🔧 Step 2: Creating test filters...")
    created_count = await create_test_filters()
    logger.info(f"✅ Created {created_count} test filters\n")
    
    # Step 3: Run scraper cycle
    logger.info("🔧 Step 3: Running scraper cycle...")
    print(f"{'='*60}")
    print("Running Scrapers")
    print(f"{'='*60}")
    
    brands = ["Rick Owens", "Raf Simons", "Comme des Garcons"]
    
    async def run_yahoo():
        async with YahooScraper() as scraper:
            return await scraper.scrape(brands=brands, max_price=None)
    
    async def run_mercari():
        async with MercariAPIScraper() as scraper:
            return await scraper.scrape(brands=brands, max_price=None)
    
    yahoo_task = asyncio.create_task(run_yahoo())
    mercari_task = asyncio.create_task(run_mercari())
    
    yahoo_listings, mercari_listings = await asyncio.gather(
        yahoo_task,
        mercari_task,
        return_exceptions=True
    )
    
    if isinstance(yahoo_listings, Exception):
        logger.error(f"❌ Yahoo scraper failed: {yahoo_listings}")
        yahoo_listings = []
    
    if isinstance(mercari_listings, Exception):
        logger.error(f"❌ Mercari scraper failed: {mercari_listings}")
        mercari_listings = []
    
    all_listings = list(yahoo_listings) + list(mercari_listings)
    logger.info(f"✅ Scraped {len(all_listings)} listings ({len(yahoo_listings)} Yahoo + {len(mercari_listings)} Mercari)\n")
    
    # Step 4: Save listings to database
    logger.info("🔧 Step 4: Saving listings to database...")
    db_stats = await save_listings_batch(all_listings)
    logger.info(
        f"✅ Database save: {db_stats.get('saved', 0)} new, "
        f"{db_stats.get('duplicates', 0)} duplicates\n"
    )
    
    # Step 5: Identify new listings (first_seen == last_seen)
    new_listings = []
    for listing in all_listings:
        if listing.first_seen and listing.last_seen:
            time_diff = abs((listing.last_seen - listing.first_seen).total_seconds())
            if time_diff < 1.0:  # Within 1 second = new listing
                new_listings.append(listing)
    
    logger.info(f"🔍 Found {len(new_listings)} new listings (out of {len(all_listings)} total)\n")
    
    # Step 6: Load active filters
    logger.info("🔧 Step 5: Loading active filters...")
    active_filters = await get_active_filters()
    logger.info(f"✅ Loaded {len(active_filters)} active filters\n")
    
    if not active_filters:
        print("⚠️  No active filters found. Cannot test matching.")
        return
    
    # Step 7: Match listings against filters
    logger.info("🔧 Step 6: Matching listings against filters...")
    filter_matcher = FilterMatcher(db_module)
    matches = await filter_matcher.get_matches_for_batch(new_listings, active_filters)
    logger.info(f"✅ Matching complete: {len(matches)} listings matched\n")
    
    # Step 8: Display results
    print(f"\n{'='*60}")
    print("Filter Matching Results")
    print(f"{'='*60}\n")
    
    if not matches:
        print("❌ No listings matched any filters")
        print("\nThis could mean:")
        print("  - No listings match the filter criteria")
        print("  - All listings are duplicates (already seen)")
        print("  - Filter criteria are too restrictive")
        return
    
    # Group matches by filter
    matches_by_filter = defaultdict(list)
    matches_by_user = defaultdict(list)
    
    for listing_id, matched_filters in matches.items():
        listing = next((l for l in new_listings if l.id == listing_id), None)
        if not listing:
            continue
        
        for filter_obj in matched_filters:
            matches_by_filter[filter_obj.name].append(listing)
            matches_by_user[filter_obj.user_id].append((listing, filter_obj))
    
    # Show matches by filter
    print("Matches by Filter:")
    print("-" * 60)
    for filter_name, listings in sorted(matches_by_filter.items()):
        print(f"\n📋 Filter: {filter_name}")
        print(f"   Matches: {len(listings)} listings")
        for listing in listings[:5]:  # Show first 5
            print(f"   - [{listing.market}] {listing.title[:60]}...")
            print(f"     Brand: {listing.brand or 'Unknown'} | Price: ¥{listing.price_jpy:,}")
        if len(listings) > 5:
            print(f"   ... and {len(listings) - 5} more")
    
    # Show matches by user
    print(f"\n{'='*60}")
    print("Alerts Per User")
    print(f"{'='*60}\n")
    
    for user_id, matches_list in sorted(matches_by_user.items()):
        # Count unique listings (a listing can match multiple filters for same user)
        unique_listings = set()
        filter_names = set()
        
        for listing, filter_obj in matches_list:
            unique_listings.add(listing.id)
            filter_names.add(filter_obj.name)
        
        # Check which alerts would actually be sent (not already sent)
        alerts_to_send = 0
        for listing, filter_obj in matches_list:
            if not await was_alert_sent(listing.id, user_id):
                alerts_to_send += 1
        
        print(f"👤 User: {user_id}")
        print(f"   Filters: {', '.join(sorted(filter_names))}")
        print(f"   Unique listings matched: {len(unique_listings)}")
        print(f"   Alerts to send: {alerts_to_send}")
        print()
    
    # Summary statistics
    print(f"{'='*60}")
    print("Summary Statistics")
    print(f"{'='*60}\n")
    print(f"Total listings scraped: {len(all_listings)}")
    print(f"  Yahoo: {len(yahoo_listings)}")
    print(f"  Mercari: {len(mercari_listings)}")
    print(f"New listings: {len(new_listings)}")
    print(f"Listings matched: {len(matches)}")
    print(f"Active filters: {len(active_filters)}")
    print(f"Users with matches: {len(matches_by_user)}")
    
    # Calculate total alerts (need to await in a loop, not a comprehension)
    total_alerts = 0
    for user_id, matches_list in matches_by_user.items():
        for listing, filter_obj in matches_list:
            if not await was_alert_sent(listing.id, user_id):
                total_alerts += 1
    
    print(f"Total alerts to send: {total_alerts}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

