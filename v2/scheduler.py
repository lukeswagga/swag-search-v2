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
    from config import SCRAPER_RUN_INTERVAL_SECONDS
except ImportError:
    from v2.scrapers.yahoo_scraper import YahooScraper
    from v2.config import SCRAPER_RUN_INTERVAL_SECONDS

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
        self._should_stop = False
    
    async def run_scraper_cycle(self) -> dict:
        """
        Run a single scraper cycle
        
        Returns:
            Dictionary with cycle results
        """
        cycle_start = datetime.now()
        self.run_count += 1
        
        logger.info(f"🔄 Starting scraper cycle #{self.run_count} at {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Brands: {', '.join(self.brands)}")
        
        try:
            async with YahooScraper() as scraper:
                listings = await scraper.scrape(
                    brands=self.brands,
                    max_price=self.max_price
                )
                
                cycle_end = datetime.now()
                duration = (cycle_end - cycle_start).total_seconds()
                
                self.total_listings_found += len(listings)
                
                # Check if we got 0 listings (might indicate rate limiting)
                if len(listings) == 0:
                    logger.warning(f"⚠️  Cycle #{self.run_count} completed in {duration:.2f}s but found 0 listings")
                    logger.warning(f"   This might indicate rate limiting or Yahoo blocking requests")
                else:
                    logger.info(f"✅ Cycle #{self.run_count} completed in {duration:.2f}s")
                    logger.info(f"   Found {len(listings)} listings")
                
                # Print results summary
                print(f"\n{'='*60}")
                print(f"Cycle #{self.run_count} Results")
                print(f"{'='*60}")
                print(f"Duration: {duration:.2f} seconds")
                print(f"Listings found: {len(listings)}")
                if len(listings) == 0:
                    print("⚠️  WARNING: 0 listings found - possible rate limiting!")
                print(f"Brands searched: {len(self.brands)}")
                
                if listings:
                    # Group by brand
                    by_brand = {}
                    for listing in listings:
                        brand = listing.brand or "Unknown"
                        by_brand[brand] = by_brand.get(brand, 0) + 1
                    
                    print(f"\nListings by brand:")
                    for brand, count in sorted(by_brand.items()):
                        print(f"  {brand}: {count}")
                    
                    # Show sample listings
                    print(f"\nSample listings (first 5):")
                    for i, listing in enumerate(listings[:5], 1):
                        print(f"  {i}. {listing.title[:60]}...")
                        print(f"     Price: ¥{listing.price_jpy:,} | Type: {listing.listing_type}")
                        print(f"     URL: {listing.url}")
                
                print(f"{'='*60}\n")
                
                self.success_count += 1
                
                return {
                    'success': True,
                    'run_number': self.run_count,
                    'duration_seconds': duration,
                    'listings_found': len(listings),
                    'listings': listings,
                    'timestamp': cycle_start.isoformat(),
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
        
        print(f"\n{'='*60}")
        print("Scraper Scheduler Started (PRODUCTION MODE - Runs Continuously)")
        print(f"{'='*60}")
        print("⚠️  WARNING: This runs CONTINUOUSLY until stopped (Ctrl+C)")
        print("⚠️  Make sure test_production_loop.py is NOT running!")
        print(f"{'='*60}")
        print(f"Run interval: {self.run_interval_seconds} seconds ({self.run_interval_seconds / 60:.1f} minutes)")
        print(f"Brands: {', '.join(self.brands)}")
        print(f"{'='*60}\n")
        
        try:
            while not self._should_stop:
                # Run scraper cycle
                result = await self.run_scraper_cycle()
                
                # Print summary statistics
                success_rate = (self.success_count / self.run_count * 100) if self.run_count > 0 else 0
                logger.info(
                    f"📊 Overall stats: {self.run_count} runs, "
                    f"{self.success_count} successful, {self.error_count} errors "
                    f"({success_rate:.1f}% success rate), "
                    f"{self.total_listings_found} total listings"
                )
                
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
        print(f"{'='*60}\n")
        
        logger.info(
            f"📊 Final stats: {self.run_count} cycles, "
            f"{self.success_count} successful, {self.error_count} errors, "
            f"{self.total_listings_found} total listings"
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

