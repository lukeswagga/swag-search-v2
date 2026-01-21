"""
Verification script to test filter matching system
Shows active filters and demonstrates matching against scraped listings
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from scrapers.yahoo_scraper import YahooScraper
    from scrapers.mercari_api_scraper import MercariAPIScraper
    from models import UserFilter, Listing
    from database import init_database, create_tables, save_listings_batch, get_active_filters, was_alert_sent
    from filter_matcher import FilterMatcher
    from config import get_database_url
    import database as db_module
except ImportError:
    from v2.scrapers.yahoo_scraper import YahooScraper
    from v2.scrapers.mercari_api_scraper import MercariAPIScraper
    from v2.models import UserFilter, Listing
    from v2.database import init_database, create_tables, save_listings_batch, get_active_filters, was_alert_sent, get_listings_since
    from v2.filter_matcher import FilterMatcher
    from v2.config import get_database_url
    from v2 import database as db_module

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def show_active_filters():
    """Display all active filters"""
    print(f"\n{'='*60}")
    print("ACTIVE USER FILTERS")
    print(f"{'='*60}\n")
    
    active_filters = await get_active_filters()
    
    if not active_filters:
        print("❌ No active filters found!")
        print("   Run: python3 v2/create_test_filters.py")
        return []
    
    for i, filter_obj in enumerate(active_filters, 1):
        import json
        brands = json.loads(filter_obj.brands) if filter_obj.brands else []
        keywords = json.loads(filter_obj.keywords) if filter_obj.keywords else []
        markets = filter_obj.markets.split(',') if filter_obj.markets else []
        
        print(f"Filter #{i}: {filter_obj.name}")
        print(f"  User ID: {filter_obj.user_id}")
        print(f"  Brands: {', '.join(brands) if brands else 'Any'}")
        print(f"  Price Range: ¥{filter_obj.price_min or 0:,} - ¥{filter_obj.price_max or '∞':,}")
        print(f"  Markets: {', '.join(markets) if markets else 'Any'}")
        print(f"  Keywords: {', '.join(keywords) if keywords else 'None'}")
        print(f"  Active: {filter_obj.active}")
        print()
    
    return active_filters


async def run_verification():
    """Run verification test"""
    
    print(f"\n{'='*60}")
    print("FILTER MATCHING VERIFICATION")
    print(f"{'='*60}\n")
    
    # Step 1: Initialize database
    logger.info("🔧 Step 1: Initializing database...")
    init_database()
    await create_tables()
    logger.info("✅ Database initialized\n")
    
    # Step 2: Show active filters
    print("Step 1: Checking Active Filters")
    print("-" * 60)
    active_filters = await show_active_filters()
    
    if not active_filters:
        print("\n⚠️  Cannot continue without active filters.")
        return
    
    # Step 3: Run scraper
    print(f"\n{'='*60}")
    print("Step 2: Running Scrapers")
    print(f"{'='*60}\n")
    
    brands = ["Rick Owens", "Raf Simons", "Comme des Garcons"]
    print(f"Scraping brands: {', '.join(brands)}\n")
    
    cycle_start = datetime.now()
    
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
    print(f"✅ Scraped {len(all_listings)} listings ({len(yahoo_listings)} Yahoo + {len(mercari_listings)} Mercari)\n")
    
    # Step 4: Save listings
    print(f"{'='*60}")
    print("Step 3: Saving Listings to Database")
    print(f"{'='*60}\n")
    
    db_stats = await save_listings_batch(all_listings)
    print(f"✅ Saved: {db_stats.get('saved', 0)} new, {db_stats.get('duplicates', 0)} duplicates\n")
    
    # Step 5: Get new listings from database
    print(f"{'='*60}")
    print("Step 4: Identifying New Listings")
    print(f"{'='*60}\n")
    
    cycle_start_time = cycle_start - timedelta(minutes=2)
    new_listings_from_db = await get_listings_since(cycle_start_time)
    
    new_listings = []
    for listing in new_listings_from_db:
        if listing.first_seen and listing.last_seen:
            time_diff = abs((listing.last_seen - listing.first_seen).total_seconds())
            if time_diff < 1.0:
                new_listings.append(listing)
    
    print(f"✅ Found {len(new_listings)} new listings (out of {len(all_listings)} total)\n")
    
    if not new_listings:
        print("⚠️  No new listings found. This might mean:")
        print("   - All listings are duplicates from previous runs")
        print("   - Try running again after some time has passed")
        print("   - Or check if scrapers are finding listings\n")
        return
    
    # Step 6: Match against filters
    print(f"{'='*60}")
    print("Step 5: Matching Listings Against Filters")
    print(f"{'='*60}\n")
    
    filter_matcher = FilterMatcher(db_module)
    matches = await filter_matcher.get_matches_for_batch(new_listings, active_filters)
    
    if not matches:
        print("❌ No listings matched any filters!")
        print("\nThis could mean:")
        print("  - Listings don't match filter criteria (brand, price, market, keywords)")
        print("  - Filter criteria are too restrictive")
        print("\nSample listings that didn't match:")
        for listing in new_listings[:3]:
            print(f"  - [{listing.market}] {listing.title[:60]}...")
            print(f"    Brand: {listing.brand or 'Unknown'} | Price: ¥{listing.price_jpy:,}")
        return
    
    print(f"✅ {len(matches)} listings matched filters!\n")
    
    # Step 7: Show detailed matches
    print(f"{'='*60}")
    print("Step 6: Detailed Match Results")
    print(f"{'='*60}\n")
    
    # Group by filter
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
    print("📋 Matches by Filter:")
    print("-" * 60)
    for filter_name, listings in sorted(matches_by_filter.items()):
        print(f"\n🔍 Filter: {filter_name}")
        print(f"   Matched {len(listings)} listing(s):")
        for listing in listings[:5]:  # Show first 5
            print(f"   ✅ [{listing.market.upper()}] {listing.title[:55]}...")
            print(f"      Brand: {listing.brand or 'Unknown'} | Price: ¥{listing.price_jpy:,}")
        if len(listings) > 5:
            print(f"   ... and {len(listings) - 5} more")
    
    # Show alerts per user
    print(f"\n{'='*60}")
    print("Step 7: Alerts That Would Be Sent")
    print(f"{'='*60}\n")
    
    for user_id, matches_list in sorted(matches_by_user.items()):
        unique_listings = set()
        filter_names = set()
        
        for listing, filter_obj in matches_list:
            unique_listings.add(listing.id)
            filter_names.add(filter_obj.name)
        
        # Check which alerts would actually be sent
        alerts_to_send = []
        for listing, filter_obj in matches_list:
            if not await was_alert_sent(listing.id, user_id):
                alerts_to_send.append((listing, filter_obj))
        
        print(f"👤 User: {user_id}")
        print(f"   Filters: {', '.join(sorted(filter_names))}")
        print(f"   Unique listings matched: {len(unique_listings)}")
        print(f"   Alerts to send: {len(alerts_to_send)}")
        
        if alerts_to_send:
            print(f"   Sample alerts:")
            for listing, filter_obj in alerts_to_send[:3]:
                print(f"     📤 [{listing.market}] {listing.title[:50]}...")
                print(f"        Matched filter: {filter_obj.name}")
                print(f"        Price: ¥{listing.price_jpy:,}")
        print()
    
    # Summary
    print(f"{'='*60}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*60}\n")
    print(f"✅ Active filters: {len(active_filters)}")
    print(f"✅ Listings scraped: {len(all_listings)}")
    print(f"✅ New listings: {len(new_listings)}")
    print(f"✅ Listings matched: {len(matches)}")
    print(f"✅ Users with matches: {len(matches_by_user)}")
    
    total_alerts = sum(
        len([m for m in matches_list if not await was_alert_sent(m[0].id, user_id)])
        for user_id, matches_list in matches_by_user.items()
    )
    print(f"✅ Total alerts ready to send: {total_alerts}")
    print(f"\n{'='*60}\n")
    
    if total_alerts > 0:
        print("🎉 SUCCESS! Filter matching is working correctly.")
        print("   The scheduler will send these alerts automatically.")
    else:
        print("ℹ️  All matching listings have already been sent alerts.")
        print("   Wait for new listings or create new filters to see alerts.")


if __name__ == "__main__":
    try:
        asyncio.run(run_verification())
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}", exc_info=True)



