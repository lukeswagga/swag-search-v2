"""
Main scheduler loop that runs scraper continuously with proper rate limiting

⚠️ IMPORTANT: Do NOT run this simultaneously with test_production_loop.py!
- This script runs CONTINUOUSLY (every 5 minutes)
- Use test_production_loop.py for testing (runs 3 cycles then stops)
- Running both at once will double your requests and risk rate limits
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
import sys
import os

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.yahoo_scraper import YahooScraper
from scrapers.mercari_api_scraper import MercariAPIScraper
from config import SCRAPER_RUN_INTERVAL_SECONDS, get_discord_webhook_url, get_discord_bot_token, get_discord_channel_id, MAX_ALERTS_PER_CYCLE, get_database_url, ALL_BRANDS, BRANDS_PER_CYCLE, CYCLE_DELAY_SECONDS
from discord_notifier import DiscordNotifier
from discord_bot import SwagSearchBot
from database import init_database, create_tables, save_listings_batch, close_database, get_active_filters, record_alert_sent, was_alert_sent, get_listings_since
from filter_matcher import FilterMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ScraperScheduler:
    """
    Main scheduler that runs scraper every N minutes with graceful error handling
    """
    
    def __init__(
        self,
        brands: List[str],
        run_interval_seconds: int = SCRAPER_RUN_INTERVAL_SECONDS,
        max_price: Optional[int] = None
    ):
        """
        Initialize scheduler
        
        Args:
            brands: List of brand names to scrape
            run_interval_seconds: How often to run scraper (default: 5 minutes)
            max_price: Optional maximum price filter (JPY)
        """
        self.brands = brands
        self.run_interval_seconds = run_interval_seconds
        self.max_price = max_price
        self.run_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_listings_found = 0
        self.total_yahoo_listings = 0
        self.total_mercari_listings = 0
        self.total_new_listings = 0
        self.total_duplicates_skipped = 0
        self.total_alerts_sent = 0
        self.total_users_alerted = 0
        self._should_stop = False
        
        # Initialize Discord bot (required for alerts)
        bot_token = get_discord_bot_token()
        self.discord_bot: Optional[SwagSearchBot] = None
        self.discord_channel_id: Optional[str] = None
        self._bot_available = False
        
        if bot_token:
            try:
                self.discord_bot = SwagSearchBot(bot_token)
                self.discord_channel_id = get_discord_channel_id()
                if self.discord_channel_id:
                    logger.info(f"✅ Discord bot initialized with channel ID: {self.discord_channel_id}")
                else:
                    logger.info("✅ Discord bot initialized (will start on scheduler start)")
                    logger.warning("⚠️  DISCORD_CHANNEL_ID not set - channel alerts disabled (set it for #v2 channel)")
                self._bot_available = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Discord bot: {e}")
                self.discord_bot = None
        else:
            logger.error("❌ DISCORD_BOT_TOKEN not set - Discord bot disabled")
            logger.error("   Discord alerts will not work. Set DISCORD_BOT_TOKEN to enable alerts.")
        
        # Webhook as emergency fallback only (if bot completely unavailable)
        webhook_url = get_discord_webhook_url()
        self.discord_notifier: Optional[DiscordNotifier] = None
        if webhook_url and not self._bot_available:
            # Only use webhook if bot is completely unavailable
            logger.warning("⚠️  Bot unavailable - using webhook as emergency fallback")
            self.discord_notifier = DiscordNotifier(webhook_url)
            logger.info("✅ Discord webhook notifier initialized (emergency fallback mode)")
        elif webhook_url:
            # Keep webhook available but don't use it (bot is primary)
            logger.debug("ℹ️  Discord webhook available but not used (bot is primary)")
        
        # Database will be initialized in run_continuous() or manually via init_database()
        self._database_initialized = False
        
        # Filter matcher (will be initialized after database is ready)
        self.filter_matcher: Optional[FilterMatcher] = None
    
    async def run_scraper_cycle(self) -> dict:
        """
        Run a single scraper cycle with both Yahoo and Mercari scrapers
        
        Returns:
            Dictionary with cycle results
        """
        cycle_start = datetime.now()
        self.run_count += 1
        
        logger.info(f"🔄 Starting scraper cycle #{self.run_count} at {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Brands: {', '.join(self.brands)}")
        logger.info(f"   Running both Yahoo and Mercari scrapers...")
        
        try:
            # Run both scrapers in parallel
            yahoo_start = datetime.now()
            mercari_start = datetime.now()
            
            async def run_yahoo():
                async with YahooScraper() as scraper:
                    return await scraper.scrape(
                        brands=self.brands,
                        max_price=self.max_price
                    )
            
            async def run_mercari():
                async with MercariAPIScraper() as scraper:
                    return await scraper.scrape(
                        brands=self.brands,
                        max_price=self.max_price
                    )
            
            # Run both scrapers concurrently
            yahoo_task = asyncio.create_task(run_yahoo())
            mercari_task = asyncio.create_task(run_mercari())
            
            yahoo_listings, mercari_listings = await asyncio.gather(
                yahoo_task,
                mercari_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(yahoo_listings, Exception):
                logger.error(f"❌ Yahoo scraper failed: {yahoo_listings}")
                yahoo_listings = []
            
            if isinstance(mercari_listings, Exception):
                logger.error(f"❌ Mercari scraper failed: {mercari_listings}")
                mercari_listings = []
            
            yahoo_duration = (datetime.now() - yahoo_start).total_seconds()
            mercari_duration = (datetime.now() - mercari_start).total_seconds()
            
            # Log individual scraper stats
            logger.info(f"📊 Yahoo: {len(yahoo_listings)} listings in {yahoo_duration:.2f}s")
            logger.info(f"📊 Mercari: {len(mercari_listings)} listings in {mercari_duration:.2f}s")
            
            # Combine listings from both sources
            all_listings = list(yahoo_listings) + list(mercari_listings)
            
            # Save all listings to database
            db_stats = None
            if not self._database_initialized:
                logger.warning(f"⚠️  Database not initialized - skipping save of {len(all_listings)} listings")
            elif not all_listings:
                logger.debug(f"ℹ️  No listings to save (empty list)")
            else:
                logger.info(f"💾 Saving {len(all_listings)} listings to database...")
                try:
                    db_stats = await save_listings_batch(all_listings)
                    self.total_new_listings += db_stats.get("saved", 0)
                    self.total_duplicates_skipped += db_stats.get("duplicates", 0)
                    logger.info(
                        f"✅ Database save complete: {db_stats.get('saved', 0)} new, "
                        f"{db_stats.get('duplicates', 0)} duplicates"
                    )
                    if db_stats.get('errors', 0) > 0:
                        logger.error(f"❌ Database save had {db_stats.get('errors', 0)} errors")
                except Exception as e:
                    logger.error(f"❌ Error saving listings to database: {e}", exc_info=True)
            
            cycle_end = datetime.now()
            total_duration = (cycle_end - cycle_start).total_seconds()
            
            # Update totals
            self.total_listings_found += len(all_listings)
            self.total_yahoo_listings += len(yahoo_listings)
            self.total_mercari_listings += len(mercari_listings)
            
            # Check if we got 0 listings (might indicate rate limiting)
            if len(all_listings) == 0:
                logger.warning(f"⚠️  Cycle #{self.run_count} completed in {total_duration:.2f}s but found 0 listings")
                logger.warning(f"   Yahoo: {len(yahoo_listings)}, Mercari: {len(mercari_listings)}")
            else:
                logger.info(f"✅ Cycle #{self.run_count} completed in {total_duration:.2f}s")
                logger.info(f"   Total: {len(all_listings)} listings ({len(yahoo_listings)} Yahoo + {len(mercari_listings)} Mercari)")
            
            # Print results summary
            print(f"\n{'='*60}")
            print(f"Cycle #{self.run_count} Results")
            print(f"{'='*60}")
            print(f"Total duration: {total_duration:.2f} seconds")
            print(f"  Yahoo: {yahoo_duration:.2f}s, {len(yahoo_listings)} listings")
            print(f"  Mercari: {mercari_duration:.2f}s, {len(mercari_listings)} listings")
            print(f"Total listings: {len(all_listings)}")
            if db_stats:
                print(f"Database stats:")
                print(f"  New listings saved: {db_stats.get('saved', 0)}")
                print(f"  Duplicates skipped: {db_stats.get('duplicates', 0)}")
                if db_stats.get('errors', 0) > 0:
                    print(f"  Errors: {db_stats.get('errors', 0)}")
            if len(all_listings) == 0:
                print("⚠️  WARNING: 0 listings found - possible rate limiting!")
            print(f"Brands searched: {len(self.brands)}")
            
            if all_listings:
                # Group by market
                by_market = {}
                for listing in all_listings:
                    market = listing.market or "Unknown"
                    by_market[market] = by_market.get(market, 0) + 1
                
                print(f"\nListings by market:")
                for market, count in sorted(by_market.items()):
                    print(f"  {market}: {count}")
                
                # Group by brand
                by_brand = {}
                for listing in all_listings:
                    brand = listing.brand or "Unknown"
                    by_brand[brand] = by_brand.get(brand, 0) + 1
                
                print(f"\nListings by brand:")
                for brand, count in sorted(by_brand.items()):
                    print(f"  {brand}: {count}")
                
                # Show sample listings (newest first - already sorted by scrapers)
                print(f"\nSample listings (top 5 newest):")
                for i, listing in enumerate(all_listings[:5], 1):
                    print(f"  {i}. [{listing.market}] {listing.title[:50]}...")
                    print(f"     Price: ¥{listing.price_jpy:,} | Type: {listing.listing_type}")
                    print(f"     URL: {listing.url}")
            
            print(f"{'='*60}\n")
            
            # Discord alerts: Send all listings to channel + DMs to matched users (bot only)
            discord_stats = None
            filter_alerts_stats = None
            if self._database_initialized and self.discord_bot and all_listings and db_stats:
                try:
                    # Get new listings from database (those saved in this cycle)
                    # Query for listings first_seen in the last 2 minutes (safety margin)
                    from datetime import timedelta
                    
                    cycle_start_time = cycle_start - timedelta(minutes=2)
                    new_listings_from_db = await get_listings_since(cycle_start_time)
                    
                    # Filter to only those that are truly new (first_seen == last_seen within 1 second)
                    new_listings = []
                    for listing in new_listings_from_db:
                        if listing.first_seen and listing.last_seen:
                            time_diff = abs((listing.last_seen - listing.first_seen).total_seconds())
                            if time_diff < 1.0:  # Within 1 second = new listing
                                new_listings.append(listing)
                    
                    if new_listings:
                        logger.info(f"🔍 Found {len(new_listings)} new listings, sending to channel and matching against user filters...")
                        
                        # Send ALL new listings to #v2 channel (public feed) using bot
                        channel_sent = 0
                        channel_failed = 0
                        
                        if not self.discord_bot:
                            logger.error("❌ Discord bot not available - cannot send alerts")
                        elif not self.discord_bot.is_ready():
                            logger.error("❌ Discord bot not ready - skipping all alerts")
                            logger.error("   Check bot connection and permissions")
                        elif not self.discord_channel_id:
                            logger.warning("⚠️  DISCORD_CHANNEL_ID not set - skipping channel alerts")
                        else:
                            # Bot is ready and channel ID is set - send all listings to channel
                            logger.info(f"📤 Sending {len(new_listings)} listings to channel #{self.discord_channel_id} using Discord bot...")
                            for listing in new_listings:
                                alert_result = await self.discord_bot.send_alert(
                                    listing=listing,
                                    channel_id=self.discord_channel_id
                                )
                                if alert_result['channel_sent']:
                                    channel_sent += 1
                                else:
                                    channel_failed += 1
                            logger.info(f"✅ Channel alerts: {channel_sent} sent, {channel_failed} failed")
                        
                        # Initialize filter matcher if not already done
                        if self.filter_matcher is None:
                            # Import database module for filter matcher
                            import database as db_module
                            self.filter_matcher = FilterMatcher(db_module)
                        
                        # Load active filters for DM matching
                        active_filters = await get_active_filters()
                        
                        if active_filters:
                            logger.info(f"📋 Loaded {len(active_filters)} active user filters")
                            
                            # Match listings against filters
                            matches = await self.filter_matcher.get_matches_for_batch(new_listings, active_filters)
                            
                            # Send personalized DMs to matched users
                            alerts_sent = 0
                            alerts_failed = 0
                            users_alerted = set()
                            
                            # Group matches by listing for efficient sending
                            for listing_id, matched_filters in matches.items():
                                # Find the listing object
                                listing = next((l for l in new_listings if l.id == listing_id), None)
                                if not listing:
                                    continue
                                
                                # Collect all users and filter names for this listing
                                user_ids = []
                                filter_names = {}
                                
                                for filter_obj in matched_filters:
                                    # Check if alert was already sent to this user for this listing
                                    if await was_alert_sent(listing_id, filter_obj.user_id):
                                        logger.debug(f"⏭️  Skipping duplicate alert: listing {listing_id} -> user {filter_obj.user_id}")
                                        continue
                                    
                                    user_ids.append(filter_obj.user_id)
                                    filter_names[filter_obj.user_id] = filter_obj.name
                                
                                # Send alert to all matched users for this listing (bot only)
                                if user_ids:
                                    if not self.discord_bot:
                                        logger.error(f"❌ Discord bot not available - skipping DM alerts for listing {listing_id}")
                                        alerts_failed += len(user_ids)
                                    elif not self.discord_bot.is_ready():
                                        logger.error(f"❌ Discord bot not ready - skipping DM alerts for listing {listing_id}")
                                        alerts_failed += len(user_ids)
                                    else:
                                        # Bot is ready - send DMs using bot
                                        alert_result = await self.discord_bot.send_alert(
                                            listing=listing,
                                            user_ids=user_ids,
                                            filter_names=filter_names
                                        )
                                        
                                        alerts_sent += alert_result['dms_sent']
                                        alerts_failed += alert_result['dms_failed']
                                        
                                        # Record successful alerts (only mark those that succeeded)
                                        # We'll record based on the success count from alert_result
                                        # Since we can't tell which specific DMs succeeded individually,
                                        # we'll mark the first N as sent (where N = alerts_sent)
                                        sent_count = 0
                                        for user_id in user_ids:
                                            if sent_count < alert_result['dms_sent']:
                                                filter_obj = next((f for f in matched_filters if f.user_id == user_id), None)
                                                if filter_obj:
                                                    users_alerted.add(user_id)
                                                    await record_alert_sent(listing_id, user_id, filter_obj.id)
                                                    sent_count += 1
                            
                            filter_alerts_stats = {
                                'total_matches': len(matches),
                                'alerts_sent': alerts_sent,
                                'alerts_failed': alerts_failed,
                                'users_alerted': len(users_alerted),
                                'channel_sent': channel_sent,
                                'channel_failed': channel_failed
                            }
                            
                            self.total_alerts_sent += alerts_sent
                            self.total_users_alerted = len(users_alerted)
                            
                            # Show detailed filter matching results
                            print(f"\n{'='*60}")
                            print("DISCORD ALERTS RESULTS")
                            print(f"{'='*60}")
                            print(f"Channel alerts: {channel_sent} sent, {channel_failed} failed")
                            print(f"Active filters checked: {len(active_filters)}")
                            print(f"New listings checked: {len(new_listings)}")
                            print(f"Listings matched: {len(matches)}")
                            print(f"DM alerts sent: {alerts_sent}")
                            print(f"DM alerts failed: {alerts_failed}")
                            print(f"Users alerted: {len(users_alerted)}")
                            
                            if matches:
                                # Group matches by filter for display
                                from collections import defaultdict
                                matches_by_filter = defaultdict(list)
                                for listing_id, matched_filters in matches.items():
                                    listing = next((l for l in new_listings if l.id == listing_id), None)
                                    if listing:
                                        for filter_obj in matched_filters:
                                            matches_by_filter[filter_obj.name].append(listing)
                                
                                print(f"\nMatches by filter:")
                                for filter_name, listings in sorted(matches_by_filter.items()):
                                    print(f"  📋 {filter_name}: {len(listings)} listing(s)")
                                    # Show sample matches
                                    for listing in listings[:2]:
                                        print(f"     - [{listing.market}] {listing.title[:50]}... (¥{listing.price_jpy:,})")
                            
                            print(f"{'='*60}\n")
                            
                            logger.info(
                                f"📊 Discord alerts complete: {channel_sent} channel messages, "
                                f"{alerts_sent} DMs sent to {len(users_alerted)} users"
                            )
                        else:
                            logger.info("ℹ️  No active user filters found, skipping filter matching")
                    else:
                        logger.info("ℹ️  No new listings found (all are duplicates), skipping Discord alerts")
                        
                except Exception as e:
                    logger.error(f"❌ Error in Discord alerts: {e}", exc_info=True)
            
            self.success_count += 1
            
            return {
                'success': True,
                'run_number': self.run_count,
                'duration_seconds': total_duration,
                'yahoo_duration': yahoo_duration,
                'mercari_duration': mercari_duration,
                'listings_found': len(all_listings),
                'yahoo_listings': len(yahoo_listings),
                'mercari_listings': len(mercari_listings),
                'listings': all_listings,
                'timestamp': cycle_start.isoformat(),
                'discord_alerts': discord_stats,
                'filter_alerts': filter_alerts_stats,
                'database_stats': db_stats,
            }
                
        except Exception as e:
            cycle_end = datetime.now()
            duration = (cycle_end - cycle_start).total_seconds()
            
            logger.error(f"❌ Cycle #{self.run_count} failed after {duration:.2f}s: {e}", exc_info=True)
            self.error_count += 1
            
            print(f"\n{'='*60}")
            print(f"Cycle #{self.run_count} Error")
            print(f"{'='*60}")
            print(f"Duration: {duration:.2f} seconds")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")
            
            return {
                'success': False,
                'run_number': self.run_count,
                'duration_seconds': duration,
                'error': str(e),
                'timestamp': cycle_start.isoformat(),
            }
    
    async def run_continuous(self):
        """
        Run scraper continuously, cycling through all brands in batches
        Cycles through all brands 3 at a time until complete, then starts over
        """
        # Use all brands from config if not specified
        all_brands = self.brands if self.brands else ALL_BRANDS
        brands_per_cycle = BRANDS_PER_CYCLE
        cycle_delay = CYCLE_DELAY_SECONDS
        
        logger.info("🚀 Starting continuous scraper scheduler")
        logger.info(f"   Total brands: {len(all_brands)}")
        logger.info(f"   Brands per cycle: {brands_per_cycle}")
        logger.info(f"   Cycle delay: {cycle_delay} seconds")
        
        # Initialize database
        try:
            logger.info("🔧 Initializing database...")
            from config import get_database_url
            db_url = get_database_url()
            if not db_url:
                logger.warning("⚠️  No DATABASE_URL found in environment - database will not be initialized")
                logger.warning("   Set DATABASE_URL in .env file or environment variables")
                self._database_initialized = False
            else:
                logger.info(f"📋 Found DATABASE_URL: {db_url.split('@')[0]}@...")
                init_database()  # Uses DATABASE_URL from environment
                
                # Verify initialization worked
                import database as db_module
                
                if db_module._session_factory is None:
                    logger.error("❌ Database session factory is None after init_database()")
                    self._database_initialized = False
                else:
                    await create_tables()
                    self._database_initialized = True
                    logger.info("✅ Database initialized and ready")
                    
                    # Initialize filter matcher
                    self.filter_matcher = FilterMatcher(db_module)
                    logger.info("✅ Filter matcher initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
            logger.warning("⚠️  Continuing without database persistence...")
            self._database_initialized = False
        
        # Start Discord bot (required for alerts)
        if self.discord_bot:
            try:
                logger.info("🚀 Starting Discord bot...")
                await self.discord_bot.start_bot()
                
                # Wait for bot to be ready (up to 10 seconds)
                wait_attempts = 0
                max_wait = 100  # 10 seconds (100 * 0.1s)
                while not self.discord_bot.is_ready() and wait_attempts < max_wait:
                    await asyncio.sleep(0.1)
                    wait_attempts += 1
                
                if self.discord_bot.is_ready():
                    logger.info("✅ Discord bot started and ready")
                    self._bot_available = True
                else:
                    logger.error("❌ Discord bot failed to become ready after 10 seconds")
                    logger.error("   Discord alerts may not work. Check bot token and permissions.")
                    self._bot_available = False
            except Exception as e:
                logger.error(f"❌ Failed to start Discord bot: {e}", exc_info=True)
                logger.error("   Discord alerts will not work. Check DISCORD_BOT_TOKEN and bot permissions.")
                self._bot_available = False
                self.discord_bot = None
        else:
            logger.error("❌ Discord bot not initialized - Discord alerts disabled")
            logger.error("   Set DISCORD_BOT_TOKEN to enable alerts")
            self._bot_available = False
        
        print(f"\n{'='*60}")
        print("Scraper Scheduler Started (PRODUCTION MODE)")
        print(f"{'='*60}")
        print("⚠️  WARNING: This runs CONTINUOUSLY until stopped (Ctrl+C)")
        print("⚠️  Make sure test_production_loop.py is NOT running!")
        print(f"{'='*60}")
        print(f"Total brands: {len(all_brands)}")
        print(f"Brands per cycle: {brands_per_cycle}")
        print(f"Cycle delay: {cycle_delay} seconds")
        print(f"Pages per brand: 2 (production mode)")
        print(f"Database: {'✅ Initialized' if self._database_initialized else '❌ Not available'}")
        print(f"Discord Bot: {'✅ Ready' if self._bot_available and self.discord_bot and self.discord_bot.is_ready() else '❌ Not available'}")
        if self.discord_channel_id:
            print(f"Channel ID: {self.discord_channel_id}")
        else:
            print(f"Channel ID: ❌ Not set (set DISCORD_CHANNEL_ID for channel alerts)")
        print(f"{'='*60}\n")
        
        try:
            while not self._should_stop:
                # Split brands into batches
                total_cycles = (len(all_brands) + brands_per_cycle - 1) // brands_per_cycle
                
                for cycle_idx in range(total_cycles):
                    if self._should_stop:
                        break
                    
                    start_idx = cycle_idx * brands_per_cycle
                    end_idx = min(start_idx + brands_per_cycle, len(all_brands))
                    current_brands = all_brands[start_idx:end_idx]
                    
                    # Update brands for this cycle
                    self.brands = current_brands
                    
                    logger.info(f"📦 Cycle {cycle_idx + 1}/{total_cycles}: Scraping {len(current_brands)} brands")
                    logger.info(f"   Brands: {', '.join(current_brands)}")
                    
                    # Run scraper cycle with current brands
                    result = await self.run_scraper_cycle()
                    
                    # Print summary statistics
                    success_rate = (self.success_count / self.run_count * 100) if self.run_count > 0 else 0
                    stats_msg = (
                        f"📊 Overall stats: {self.run_count} cycles, "
                        f"{self.success_count} successful, {self.error_count} errors "
                        f"({success_rate:.1f}% success rate), "
                        f"{self.total_listings_found} total listings "
                        f"({self.total_yahoo_listings} Yahoo + {self.total_mercari_listings} Mercari)"
                    )
                    if self._database_initialized:
                        stats_msg += (
                            f", {self.total_new_listings} new saved, "
                            f"{self.total_duplicates_skipped} duplicates skipped"
                        )
                    logger.info(stats_msg)
                    
                    # Short delay before next cycle (unless it's the last cycle)
                    if not self._should_stop and cycle_idx < total_cycles - 1:
                        logger.info(f"⏳ Waiting {cycle_delay} seconds before next brand batch...")
                        await asyncio.sleep(cycle_delay)
                
                # After completing all brands, start over immediately
                if not self._should_stop:
                    logger.info(f"🔄 Completed all {len(all_brands)} brands. Starting over...")
                    await asyncio.sleep(cycle_delay)  # Brief pause before restarting
                    
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user (KeyboardInterrupt)")
            print(f"\n{'='*60}")
            print("Scheduler Stopped by User")
            print(f"{'='*60}")
        except Exception as e:
            logger.error(f"❌ Scheduler crashed: {e}", exc_info=True)
            print(f"\n{'='*60}")
            print("Scheduler Crashed")
            print(f"{'='*60}")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")
        finally:
            # Clean up Discord bot
            if self.discord_bot:
                try:
                    await self.discord_bot.close()
                    logger.info("✅ Discord bot closed")
                except Exception as e:
                    logger.error(f"❌ Error closing Discord bot: {e}")
            
            # Clean up Discord notifier (emergency fallback, rarely used)
            if self.discord_notifier:
                try:
                    await self.discord_notifier.close()
                    logger.info("✅ Discord webhook notifier closed")
                except Exception as e:
                    logger.error(f"❌ Error closing Discord notifier: {e}")
            
            # Clean up Discord notifier (emergency fallback, rarely used)
            if self.discord_notifier:
                try:
                    await self.discord_notifier.close()
                    logger.info("✅ Discord webhook notifier closed")
                except Exception as e:
                    logger.error(f"❌ Error closing Discord notifier: {e}")
            
            # Close database connections
            if self._database_initialized:
                try:
                    await close_database()
                    logger.info("✅ Database connections closed")
                except Exception as e:
                    logger.error(f"❌ Error closing database: {e}")
            
            self.print_final_stats()
    
    def stop(self):
        """Stop the scheduler gracefully"""
        logger.info("🛑 Stopping scheduler...")
        self._should_stop = True
    
    def print_final_stats(self):
        """Print final statistics"""
        success_rate = (self.success_count / self.run_count * 100) if self.run_count > 0 else 0
        
        print(f"\n{'='*60}")
        print("Final Statistics")
        print(f"{'='*60}")
        print(f"Total cycles: {self.run_count}")
        print(f"Successful: {self.success_count}")
        print(f"Errors: {self.error_count}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Total listings found: {self.total_listings_found}")
        print(f"  Yahoo: {self.total_yahoo_listings}")
        print(f"  Mercari: {self.total_mercari_listings}")
        if self._database_initialized:
            print(f"Database stats:")
            print(f"  New listings saved: {self.total_new_listings}")
            print(f"  Duplicates skipped: {self.total_duplicates_skipped}")
        print(f"{'='*60}\n")
        
        logger.info(
            f"📊 Final stats: {self.run_count} cycles, "
            f"{self.success_count} successful, {self.error_count} errors, "
            f"{self.total_listings_found} total listings "
            f"({self.total_yahoo_listings} Yahoo + {self.total_mercari_listings} Mercari)"
        )
        if self._database_initialized:
            logger.info(
                f"💾 Database: {self.total_new_listings} new saved, "
                f"{self.total_duplicates_skipped} duplicates skipped"
            )


async def main():
    """Main entry point for scheduler"""
    # Use all brands from config (will be cycled through 3 at a time)
    scheduler = ScraperScheduler(
        brands=[],  # Empty list means use ALL_BRANDS from config
        run_interval_seconds=SCRAPER_RUN_INTERVAL_SECONDS
    )
    
    await scheduler.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())

