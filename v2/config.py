"""
Configuration for v2 scrapers
"""
import os
from typing import Optional

# Yahoo Auctions Configuration
YAHOO_BASE_URL = "https://auctions.yahoo.co.jp"
YAHOO_SEARCH_URL = "https://auctions.yahoo.co.jp/search/search"
YAHOO_FASHION_CATEGORY = "2084005438"  # Fashion & Accessories category

# Rate Limiting
YAHOO_RATE_LIMIT_DELAY = 0.1  # Base delay between requests (seconds)
YAHOO_MAX_RETRIES = 3  # Max retries for 500 errors
YAHOO_RETRY_BACKOFF_BASE = 2  # Exponential backoff base (2^attempt)
YAHOO_TIMEOUT = 15  # Request timeout in seconds
YAHOO_CONNECT_TIMEOUT = 5  # Connection timeout in seconds

# Concurrency Settings
MAX_CONCURRENT_REQUESTS = 100  # Process 100 listings in parallel
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

