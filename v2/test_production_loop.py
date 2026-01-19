"""
Test script to run scheduler for 3 cycles (15 minutes total)
Tracks success rate and timing, logs to file

⚠️ IMPORTANT: Do NOT run this simultaneously with scheduler.py!
- This script runs for 3 cycles then STOPS (for testing)
- Use scheduler.py for production (runs continuously)
- Running both at once will double your requests and risk rate limits
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from scheduler import ScraperScheduler
    from config import SCRAPER_RUN_INTERVAL_SECONDS
except ImportError:
    from v2.scheduler import ScraperScheduler
    from v2.config import SCRAPER_RUN_INTERVAL_SECONDS

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
    """
    
    def __init__(self, brands, max_cycles: int = 3, **kwargs):
        """
        Initialize test scheduler
        
        Args:
            brands: List of brand names to scrape
            max_cycles: Maximum number of cycles to run
            **kwargs: Additional arguments for ScraperScheduler
        """
        super().__init__(brands, **kwargs)
        self.max_cycles = max_cycles
        self.cycle_results = []
    
    async def run_continuous(self):
        """
        Run scraper for limited number of cycles
        """
        logger.info("🧪 Starting test scheduler")
        logger.info(f"   Max cycles: {self.max_cycles}")
        logger.info(f"   Interval: {self.run_interval_seconds} seconds")
        logger.info(f"   Brands: {', '.join(self.brands)}")
        logger.info(f"   Log file: {log_file}")
        
        print(f"\n{'='*60}")
        print("Test Scheduler Started (TEST MODE - Runs 3 Cycles Then Stops)")
        print(f"{'='*60}")
        print("⚠️  WARNING: Make sure scheduler.py is NOT running!")
        print(f"{'='*60}")
        print(f"Max cycles: {self.max_cycles}")
        print(f"Interval: {self.run_interval_seconds} seconds ({self.run_interval_seconds / 60:.1f} minutes)")
        print(f"Total test duration: ~{self.max_cycles * self.run_interval_seconds / 60:.1f} minutes")
        print(f"Brands: {', '.join(self.brands)}")
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
                    f"{self.total_listings_found} total listings"
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
        
        if self.cycle_results:
            print(f"\nCycle Details:")
            for result in self.cycle_results:
                status = "✅" if result.get('success') else "❌"
                cycle_num = result.get('run_number', '?')
                duration = result.get('duration_seconds', 0)
                if result.get('success'):
                    listings = result.get('listings_found', 0)
                    print(f"  {status} Cycle #{cycle_num}: {duration:.2f}s, {listings} listings")
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
            f"{self.total_listings_found} total listings, "
            f"{total_duration:.2f}s total duration"
        )
        logger.info(f"📝 Full log saved to: {log_file}")


async def main():
    """Main entry point for test"""
    # Example brands - replace with your actual brands
    brands = ["Supreme", "Bape", "Nike"]
    
    # Run for 3 cycles (15 minutes total with 5-minute intervals)
    scheduler = TestScheduler(
        brands=brands,
        max_cycles=3,
        run_interval_seconds=SCRAPER_RUN_INTERVAL_SECONDS
    )
    
    await scheduler.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())

