"""
Configuration for v2 scrapers
"""
import os
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env file from project root (parent directory)
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

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

# Pagination configuration
# Production mode: 2 pages per brand
MIN_PAGES = 1  # Always scrape at least page 1
MAX_PAGES = 2  # Production: 2 pages per brand
# Note: Deduplication is handled by database when saving, not during pagination

# Brand cycling configuration
# All brands from brands.json (30 brands total)
ALL_BRANDS = [
    "14th Addiction",
    "Alyx",
    "Balenciaga",
    "Balmain",
    "Bottega Veneta",
    "Chrome Hearts",
    "Comme Des Garcons",
    "Comme des Garcons Homme Plus",
    "Dior",
    "Dolce & Gabbana",
    "Doublet",
    "Hedi Slimane",
    "Helmut Lang",
    "Hysteric Glamour",
    "Issey Miyake",
    "Jean Paul Gaultier",
    "Junya Watanabe",
    "Kiko Kostadinov",
    "LGB",
    "Maison Margiela",
    "Martine Rose",
    "Number Nine",
    "Prada",
    "Raf Simons",
    "Rick Owens",
    "Sacai",
    "Saint Laurent",
    "Takahiromiyashita The Soloist",
    "Thom Browne",
    "Vetements",
    "Yohji Yamamoto"
]

BRANDS_PER_CYCLE = 3  # Scrape 3 brands per cycle
CYCLE_DELAY_SECONDS = 10  # Short delay between cycles (10 seconds)

# Database Configuration
def get_database_url() -> Optional[str]:
    """Get database connection string from environment"""
    # Try DATABASE_PUBLIC_URL first (Railway), then DATABASE_URL
    return os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')

# Discord Configuration
def get_discord_webhook_url() -> Optional[str]:
    """Get Discord webhook URL from environment"""
    return os.getenv('DISCORD_WEBHOOK_URL')

MAX_ALERTS_PER_CYCLE = 10  # Maximum number of listings to send to Discord per cycle

# Mercari Configuration
MERCARI_BASE_URL = "https://jp.mercari.com"
MERCARI_SEARCH_URL = "https://jp.mercari.com/search"

# Rate Limiting - Mercari
# Conservative settings for Playwright (browser automation is slower)
MERCARI_MAX_REQUESTS_PER_MINUTE = 80  # Same as Yahoo
MERCARI_MIN_DELAY_BETWEEN_REQUESTS = 0.5  # Minimum delay between requests (seconds)
MERCARI_MAX_RETRIES = 3  # Max retries for 500/429 errors
MERCARI_RETRY_BACKOFF_BASE = 2  # Exponential backoff base (2^attempt)
MERCARI_TIMEOUT = 30  # Request timeout in seconds (Playwright needs more time)

# Browser Settings
HEADLESS_BROWSER = os.getenv('HEADLESS_BROWSER', 'True').lower() == 'true'  # Default to True for Railway deployment

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

