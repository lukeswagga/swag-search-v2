"""
Configuration for v2 scrapers
"""
import os
from typing import Optional

# Yahoo Auctions Configuration
YAHOO_BASE_URL = "https://auctions.yahoo.co.jp"
YAHOO_SEARCH_URL = "https://auctions.yahoo.co.jp/search/search"
YAHOO_FASHION_CATEGORY = "2084005438"  # Fashion & Accessories category

# Rate Limiting - Yahoo Auctions
# Balanced settings: fast enough to be useful, conservative enough to avoid bans
YAHOO_MAX_REQUESTS_PER_MINUTE = 80  # Balanced limit (was 100, then 60)
YAHOO_MIN_DELAY_BETWEEN_REQUESTS = 0.3  # Minimum delay between requests (seconds) - prevents bursts
YAHOO_REQUEST_DELAY_MIN = 0.5  # Minimum random delay between requests (seconds)
YAHOO_REQUEST_DELAY_MAX = 1.5  # Maximum random delay between requests (seconds)
YAHOO_MAX_RETRIES = 3  # Max retries for 500/429 errors
YAHOO_RETRY_BACKOFF_BASE = 2  # Exponential backoff base (2^attempt)
YAHOO_TIMEOUT = 15  # Request timeout in seconds
YAHOO_CONNECT_TIMEOUT = 5  # Connection timeout in seconds

# Scraper Intervals
SCRAPER_RUN_INTERVAL_SECONDS = 300  # Run scraper every 5 minutes (300 seconds)

# Concurrency Settings
# Balanced: allow some parallelization but not too aggressive
MAX_CONCURRENT_REQUESTS = 20  # Balanced limit (was 100, then 10)
MAX_PARALLEL_PAGES_PER_BRAND = 4  # Max pages to fetch in parallel per brand (balanced)
BATCH_SIZE = 100  # Process listings in batches of 100

# Database Configuration
def get_database_url() -> Optional[str]:
    """Get database connection string from environment"""
    # Try DATABASE_PUBLIC_URL first (Railway), then DATABASE_URL
    return os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')

# Request Headers
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ja,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

