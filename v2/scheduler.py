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

try:
    from scrapers.yahoo_scraper import YahooScraper
    from scrapers.mercari_api_scraper import MercariAPIScraper
    from config import SCRAPER_RUN_INTERVAL_SECONDS, get_discord_webhook_url, MAX_ALERTS_PER_CYCLE, get_database_url
    from discord_notifier import DiscordNotifier
    from database import init_database, create_tables, save_listings_batch, close_database
except ImportError:
    from v2.scrapers.yahoo_scraper import YahooScraper
    from v2.scrapers.mercari_api_scraper import MercariAPIScraper
    from v2.config import SCRAPER_RUN_INTERVAL_SECONDS, get_discord_webhook_url, MAX_ALERTS_PER_CYCLE, get_database_url
    from v2.discord_notifier import DiscordNotifier
    from v2.database import init_database, create_tables, save_listings_batch, close_database

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
        self._should_stop = False
        
        # Initialize Discord notifier if webhook URL is available
        webhook_url = get_discord_webhook_url()
        self.discord_notifier: Optional[DiscordNotifier] = None
        if webhook_url:
            self.discord_notifier = DiscordNotifier(webhook_url)
            logger.info("✅ Discord notifier initialized")
        else:
            logger.warning("⚠️  DISCORD_WEBHOOK_URL not set - Discord alerts disabled")
        
        # Database will be initialized in run_continuous() or manually via init_database()
        self._database_initialized = False
    
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
            if self._database_initialized and all_listings:
                logger.info(f"💾 Saving {len(all_listings)} listings to database...")
                try:
                    db_stats = await save_listings_batch(all_listings)
                    self.total_new_listings += db_stats.get("saved", 0)
                    self.total_duplicates_skipped += db_stats.get("duplicates", 0)
                    logger.info(
                        f"✅ Database save complete: {db_stats.get('saved', 0)} new, "
                        f"{db_stats.get('duplicates', 0)} duplicates"
                    )
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
            
            # Send top listings to Discord if notifier is available
            discord_stats = None
            if self.discord_notifier and all_listings:
                # Select top listings (already sorted newest-first by scrapers)
                # Keep the order from scrapers - newest listings first
                top_listings = all_listings[:MAX_ALERTS_PER_CYCLE]
                
                if top_listings:
                    logger.info(f"📤 Sending top {len(top_listings)} listings to Discord...")
                    discord_stats = await self.discord_notifier.send_listings(top_listings)
                    logger.info(
                        f"✅ Discord alerts sent: {discord_stats['sent']} successful, "
                        f"{discord_stats['failed']} failed"
                    )
            
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
        Run scraper continuously with intervals
        """
        logger.info("🚀 Starting continuous scraper scheduler")
        logger.info(f"   Interval: {self.run_interval_seconds} seconds ({self.run_interval_seconds / 60:.1f} minutes)")
        logger.info(f"   Brands: {', '.join(self.brands)}")
        
        # Initialize database
        try:
            logger.info("🔧 Initializing database...")
            init_database()  # Uses DATABASE_URL from environment
            await create_tables()
            self._database_initialized = True
            logger.info("✅ Database initialized and ready")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
            logger.warning("⚠️  Continuing without database persistence...")
            self._database_initialized = False
        
        print(f"\n{'='*60}")
        print("Scraper Scheduler Started (PRODUCTION MODE - Runs Continuously)")
        print(f"{'='*60}")
        print("⚠️  WARNING: This runs CONTINUOUSLY until stopped (Ctrl+C)")
        print("⚠️  Make sure test_production_loop.py is NOT running!")
        print(f"{'='*60}")
        print(f"Run interval: {self.run_interval_seconds} seconds ({self.run_interval_seconds / 60:.1f} minutes)")
        print(f"Brands: {', '.join(self.brands)}")
        print(f"Database: {'✅ Initialized' if self._database_initialized else '❌ Not available'}")
        print(f"{'='*60}\n")
        
        try:
            while not self._should_stop:
                # Run scraper cycle
                result = await self.run_scraper_cycle()
                
                # Print summary statistics
                success_rate = (self.success_count / self.run_count * 100) if self.run_count > 0 else 0
                stats_msg = (
                    f"📊 Overall stats: {self.run_count} runs, "
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
                
                # Wait before next cycle (unless we should stop)
                if not self._should_stop:
                    logger.info(f"⏳ Waiting {self.run_interval_seconds} seconds before next cycle...")
                    await asyncio.sleep(self.run_interval_seconds)
                    
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
            # Clean up Discord notifier
            if self.discord_notifier:
                await self.discord_notifier.close()
            
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
    # Example brands - replace with your actual brands
    brands = ["Supreme", "Bape", "Nike"]
    
    scheduler = ScraperScheduler(
        brands=brands,
        run_interval_seconds=SCRAPER_RUN_INTERVAL_SECONDS
    )
    
    await scheduler.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())

