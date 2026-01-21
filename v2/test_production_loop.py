"""
Test script to run scheduler for 2 cycles (10 minutes total)
Tracks success rate and timing, logs to file
Tests both Yahoo and Mercari scrapers together

⚠️ IMPORTANT: Do NOT run this simultaneously with scheduler.py!
- This script runs for 2 cycles then STOPS (for testing)
- Use scheduler.py for production (runs continuously)
- Running both at once will double your requests and risk rate limits
"""
import asyncio
import logging
import sys
import os
import random
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from scheduler import ScraperScheduler
    from config import SCRAPER_RUN_INTERVAL_SECONDS, MAX_ALERTS_PER_CYCLE
    from scrapers.yahoo_scraper import YahooScraper
    from scrapers.mercari_api_scraper import MercariAPIScraper
except ImportError:
    from v2.scheduler import ScraperScheduler
    from v2.config import SCRAPER_RUN_INTERVAL_SECONDS, MAX_ALERTS_PER_CYCLE
    from v2.scrapers.yahoo_scraper import YahooScraper
    from v2.scrapers.mercari_api_scraper import MercariAPIScraper

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure logging to both file and console
log_file = logs_dir / "test_run.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TestScheduler(ScraperScheduler):
    """
    Test scheduler that runs for a limited number of cycles
    Tests both Yahoo and Mercari scrapers together
    Sends top 10 from each market separately for testing
    """
    
    def __init__(self, brands, max_cycles: int = 2, **kwargs):
        """
        Initialize test scheduler
        
        Args:
            brands: List of brand names to scrape
            max_cycles: Maximum number of cycles to run (default: 2)
            **kwargs: Additional arguments for ScraperScheduler
        """
        super().__init__(brands, **kwargs)
        self.max_cycles = max_cycles
        self.cycle_results = []
    
    async def run_scraper_cycle(self) -> dict:
        """
        Override to send top 10 from each market separately (for testing)
        Temporarily disables Discord in parent, then sends separately
        """
        # Temporarily disable Discord notifier to prevent parent from sending
        original_notifier = self.discord_notifier
        self.discord_notifier = None
        
        # Call parent method (won't send Discord)
        result = await super().run_scraper_cycle()
        
        # Restore notifier
        self.discord_notifier = original_notifier
        
        # If cycle was successful and we have listings, send top 10 from each market
        if result.get('success') and self.discord_notifier:
            all_listings = result.get('listings', [])
            
            if all_listings:
                # Separate listings by market
                yahoo_listings = [l for l in all_listings if l.market == 'yahoo']
                mercari_listings = [l for l in all_listings if l.market == 'mercari']
                
                # Keep listings in newest-first order (already sorted by scrapers)
                # Take first 10 from each (newest listings)
                top_yahoo = yahoo_listings[:10]
                top_mercari = mercari_listings[:10]
                
                # Send Yahoo listings first
                if top_yahoo:
                    logger.info(f"📤 [TEST MODE] Sending {len(top_yahoo)} newest Yahoo listings to Discord...")
                    yahoo_stats = await self.discord_notifier.send_listings(top_yahoo)
                    logger.info(
                        f"✅ Yahoo alerts sent: {yahoo_stats['sent']} successful, "
                        f"{yahoo_stats['failed']} failed"
                    )
                else:
                    logger.warning("⚠️  No Yahoo listings to send")
                    yahoo_stats = {'sent': 0, 'failed': 0, 'total': 0}
                
                # Send Mercari listings second
                if top_mercari:
                    logger.info(f"📤 [TEST MODE] Sending {len(top_mercari)} newest Mercari listings to Discord...")
                    mercari_stats = await self.discord_notifier.send_listings(top_mercari)
                    logger.info(
                        f"✅ Mercari alerts sent: {mercari_stats['sent']} successful, "
                        f"{mercari_stats['failed']} failed"
                    )
                else:
                    logger.warning("⚠️  No Mercari listings to send")
                    mercari_stats = {'sent': 0, 'failed': 0, 'total': 0}
                
                # Update result with combined stats
                result['discord_alerts'] = {
                    'yahoo': yahoo_stats,
                    'mercari': mercari_stats,
                    'total_sent': yahoo_stats.get('sent', 0) + mercari_stats.get('sent', 0),
                    'total_failed': yahoo_stats.get('failed', 0) + mercari_stats.get('failed', 0)
                }
        
        return result
    
    async def run_continuous(self):
        """
        Run scraper for limited number of cycles
        """
        logger.info("🧪 Starting test scheduler")
        logger.info(f"   Max cycles: {self.max_cycles}")
        logger.info(f"   Interval: {self.run_interval_seconds} seconds")
        logger.info(f"   Brands: {', '.join(self.brands)}")
        logger.info(f"   Scrapers: Yahoo + Mercari (both run together)")
        logger.info(f"   Log file: {log_file}")
        
        # Initialize database (same as parent)
        try:
            logger.info("🔧 Initializing database...")
            from database import init_database, create_tables
            init_database()
            await create_tables()
            self._database_initialized = True
            logger.info("✅ Database initialized and ready")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
            logger.warning("⚠️  Continuing without database persistence...")
            self._database_initialized = False
        
        print(f"\n{'='*60}")
        print("Test Scheduler Started (TEST MODE - Runs 2 Cycles Then Stops)")
        print(f"{'='*60}")
        print("⚠️  WARNING: Make sure scheduler.py is NOT running!")
        print(f"{'='*60}")
        print(f"Max cycles: {self.max_cycles}")
        print(f"Interval: {self.run_interval_seconds} seconds ({self.run_interval_seconds / 60:.1f} minutes)")
        print(f"Total test duration: ~{self.max_cycles * self.run_interval_seconds / 60:.1f} minutes")
        print(f"Brands: {', '.join(self.brands)}")
        print(f"Scrapers: Yahoo + Mercari (both run together)")
        print(f"Database: {'✅ Initialized' if self._database_initialized else '❌ Not available'}")
        print(f"Log file: {log_file}")
        print(f"{'='*60}\n")
        
        test_start = datetime.now()
        
        try:
            for cycle_num in range(1, self.max_cycles + 1):
                if self._should_stop:
                    break
                
                # Run scraper cycle
                result = await self.run_scraper_cycle()
                self.cycle_results.append(result)
                
                # Print summary statistics
                success_rate = (self.success_count / self.run_count * 100) if self.run_count > 0 else 0
                logger.info(
                    f"📊 Progress: {self.run_count}/{self.max_cycles} cycles, "
                    f"{self.success_count} successful, {self.error_count} errors "
                    f"({success_rate:.1f}% success rate), "
                    f"{self.total_listings_found} total listings "
                    f"({self.total_yahoo_listings} Yahoo + {self.total_mercari_listings} Mercari)"
                )
                
                # Wait before next cycle (unless this was the last one)
                if cycle_num < self.max_cycles and not self._should_stop:
                    logger.info(f"⏳ Waiting {self.run_interval_seconds} seconds before next cycle...")
                    await asyncio.sleep(self.run_interval_seconds)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Test scheduler stopped by user (KeyboardInterrupt)")
            print(f"\n{'='*60}")
            print("Test Scheduler Stopped by User")
            print(f"{'='*60}")
        except Exception as e:
            logger.error(f"❌ Test scheduler crashed: {e}", exc_info=True)
            print(f"\n{'='*60}")
            print("Test Scheduler Crashed")
            print(f"{'='*60}")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")
        finally:
            test_end = datetime.now()
            total_duration = (test_end - test_start).total_seconds()
            
            # Clean up Discord notifier
            if self.discord_notifier:
                try:
                    await self.discord_notifier.close()
                except Exception as e:
                    logger.warning(f"Error closing Discord notifier: {e}")
            
            # Clean up database connections (if initialized)
            if hasattr(self, '_database_initialized') and self._database_initialized:
                try:
                    from database import close_database
                    await close_database()
                    logger.info("✅ Database connections closed")
                except Exception as e:
                    logger.error(f"❌ Error closing database: {e}")
            
            self.print_test_results(total_duration)
    
    def print_test_results(self, total_duration: float):
        """Print detailed test results"""
        success_rate = (self.success_count / self.run_count * 100) if self.run_count > 0 else 0
        
        print(f"\n{'='*60}")
        print("Test Results Summary")
        print(f"{'='*60}")
        print(f"Total test duration: {total_duration:.2f} seconds ({total_duration / 60:.2f} minutes)")
        print(f"Cycles completed: {self.run_count}/{self.max_cycles}")
        print(f"Successful cycles: {self.success_count}")
        print(f"Failed cycles: {self.error_count}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Total listings found: {self.total_listings_found}")
        print(f"  Yahoo: {self.total_yahoo_listings}")
        print(f"  Mercari: {self.total_mercari_listings}")
        
        if self.cycle_results:
            print(f"\nCycle Details:")
            for result in self.cycle_results:
                status = "✅" if result.get('success') else "❌"
                cycle_num = result.get('run_number', '?')
                duration = result.get('duration_seconds', 0)
                if result.get('success'):
                    listings = result.get('listings_found', 0)
                    yahoo_listings = result.get('yahoo_listings', 0)
                    mercari_listings = result.get('mercari_listings', 0)
                    yahoo_duration = result.get('yahoo_duration', 0)
                    mercari_duration = result.get('mercari_duration', 0)
                    print(f"  {status} Cycle #{cycle_num}: {duration:.2f}s total, {listings} listings")
                    print(f"      Yahoo: {yahoo_duration:.2f}s, {yahoo_listings} listings")
                    print(f"      Mercari: {mercari_duration:.2f}s, {mercari_listings} listings")
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"  {status} Cycle #{cycle_num}: {duration:.2f}s, Error: {error[:60]}")
        
        # Calculate average cycle time
        if self.cycle_results:
            avg_duration = sum(r.get('duration_seconds', 0) for r in self.cycle_results) / len(self.cycle_results)
            print(f"\nAverage cycle duration: {avg_duration:.2f} seconds")
        
        print(f"{'='*60}\n")
        
        logger.info(
            f"📊 Test complete: {self.run_count} cycles, "
            f"{self.success_count} successful, {self.error_count} errors, "
            f"{self.total_listings_found} total listings "
            f"({self.total_yahoo_listings} Yahoo + {self.total_mercari_listings} Mercari), "
            f"{total_duration:.2f}s total duration"
        )
        logger.info(f"📝 Full log saved to: {log_file}")


async def main():
    """Main entry point for test"""
    # Brands matching the test filters
    brands = ["Rick Owens", "Raf Simons", "Comme des Garcons"]
    
    # Run for 2 cycles (10 minutes total with 5-minute intervals)
    scheduler = TestScheduler(
        brands=brands,
        max_cycles=2,
        run_interval_seconds=SCRAPER_RUN_INTERVAL_SECONDS
    )
    
    await scheduler.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())

