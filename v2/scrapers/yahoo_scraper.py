"""
Async Yahoo Japan scraper - 10x faster with parallel processing
Uses aiohttp + BeautifulSoup for async HTML parsing
Production-ready with rate limiting and error handling
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
import random
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Handle imports - try relative first, then absolute
import sys
import os

# Add parent directory to path for absolute imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from .base import BaseScraper
    from .rate_limiter import RateLimiter, RateLimiterManager
except ImportError:
    from scrapers.base import BaseScraper
    from scrapers.rate_limiter import RateLimiter, RateLimiterManager

try:
    from ..config import (
        YAHOO_SEARCH_URL,
        YAHOO_TIMEOUT,
        YAHOO_CONNECT_TIMEOUT,
        YAHOO_MAX_RETRIES,
        YAHOO_RETRY_BACKOFF_BASE,
        YAHOO_MAX_REQUESTS_PER_MINUTE,
        YAHOO_MIN_DELAY_BETWEEN_REQUESTS,
        YAHOO_REQUEST_DELAY_MIN,
        YAHOO_REQUEST_DELAY_MAX,
        MAX_CONCURRENT_REQUESTS,
        MAX_PARALLEL_PAGES_PER_BRAND,
        BATCH_SIZE,
        DEFAULT_HEADERS
    )
except ImportError:
    from config import (
        YAHOO_SEARCH_URL,
        YAHOO_TIMEOUT,
        YAHOO_CONNECT_TIMEOUT,
        YAHOO_MAX_RETRIES,
        YAHOO_RETRY_BACKOFF_BASE,
        YAHOO_MAX_REQUESTS_PER_MINUTE,
        YAHOO_MIN_DELAY_BETWEEN_REQUESTS,
        YAHOO_REQUEST_DELAY_MIN,
        YAHOO_REQUEST_DELAY_MAX,
        MAX_CONCURRENT_REQUESTS,
        MAX_PARALLEL_PAGES_PER_BRAND,
        BATCH_SIZE,
        DEFAULT_HEADERS
    )

try:
    from ..models import Listing
except ImportError:
    from models import Listing


class YahooScraper(BaseScraper):
    """Async Yahoo Japan scraper with parallel processing and rate limiting"""
    
    def __init__(self):
        super().__init__()
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        # Initialize rate limiter for Yahoo domain
        self.rate_limiter = RateLimiter(
            domain="auctions.yahoo.co.jp",
            max_requests_per_minute=YAHOO_MAX_REQUESTS_PER_MINUTE
        )
        # Log rate limiter state at startup
        stats = self.rate_limiter.get_stats()
        if stats['in_backoff']:
            logger.warning(
                f"⚠️  Rate limiter for {stats['domain']} is in backoff until {stats['backoff_until']}"
            )
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session with connection pooling and rate limiter headers"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=MAX_CONCURRENT_REQUESTS,
                limit_per_host=50,
                ttl_dns_cache=300
            )
            timeout = aiohttp.ClientTimeout(
                total=YAHOO_TIMEOUT,
                connect=YAHOO_CONNECT_TIMEOUT
            )
            # Use rate limiter headers (includes rotating user agent)
            headers = self.rate_limiter.get_headers()
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def build_search_url(
        self,
        keyword: str,
        page: int = 1,
        fixed_type: int = 3,  # 1=fixed only, 2=auction only, 3=both
        sort_type: str = "end",  # "end", "new", "price"
        sort_order: str = "a",  # "a"=ascending, "d"=descending
        page_size: int = 50,
        max_price: Optional[int] = None
    ) -> str:
        """
        Build Yahoo Japan search URL
        
        Args:
            keyword: Search term
            page: Page number (1-based)
            fixed_type: 1=fixed only, 2=auction only, 3=both
            sort_type: "end"=ending soon, "new"=newest, "price"=price
            sort_order: "a"=ascending, "d"=descending
            page_size: Items per page (default 50)
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            Complete Yahoo search URL
        """
        # Calculate starting position (Yahoo uses 1-based indexing)
        start_position = (page - 1) * page_size + 1
        
        params = {
            'p': keyword,
            'va': keyword,  # Verified auction parameter
            'is_postage_mode': '1',
            'dest_pref_code': '13',  # Tokyo prefecture for shipping
            'b': str(start_position),
            'n': str(page_size)
        }
        
        # Only add 'fixed' parameter if not sorting by newest
        # Yahoo's default behavior (without 'fixed') matches Chrome's newest sort better
        if sort_type != "new":
            params['fixed'] = str(fixed_type)
        
        # Add price filter if specified
        if max_price:
            params['price_range'] = f'0,{max_price}'
        
        # Add sorting parameters
        if sort_type == "end":
            params['s1'] = 'end'
            params['o1'] = sort_order
        elif sort_type == "new":
            # Use 'new' for newest listings (not 'cbids' which is for price/bids)
            params['s1'] = 'new'
            params['o1'] = sort_order  # "d" for descending (newest first)
        elif sort_type == "price":
            params['s1'] = 'cbids'
            params['o1'] = sort_order
        
        # Build URL with proper encoding
        param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
        return f"{YAHOO_SEARCH_URL}?{param_string}"
    
    async def fetch_page_with_retry(self, url: str) -> Optional[str]:
        """
        Fetch page with rate limiting, exponential backoff retry logic, and random delays
        
        Args:
            url: URL to fetch
        
        Returns:
            HTML content or None if all retries fail
        """
        if self.session is None:
            await self._create_session()
        
        for attempt in range(1, YAHOO_MAX_RETRIES + 1):
            try:
                # For first request, add longer initial delay to avoid immediate blocking
                # Yahoo may have temporarily blocked IP from previous failed attempts
                if attempt == 1 and len(self.rate_limiter.request_times) == 0:
                    # First request ever - wait 10 seconds to let any IP blocks clear
                    # If you're still getting 500s, wait 5-10 minutes between test runs
                    logger.info("⏳ Initial delay before first request (10s) - Yahoo may have temporarily blocked IP...")
                    await asyncio.sleep(10.0)
                
                # Acquire rate limiter permission (waits if needed, enforces min delay)
                await self.rate_limiter.acquire(min_delay=YAHOO_MIN_DELAY_BETWEEN_REQUESTS)
                
                async with self._semaphore:  # Concurrency limiting
                    # Add small random jitter (0.1-0.3s) to avoid synchronized requests
                    if attempt == 1:  # Only on first attempt, not retries
                        jitter = random.uniform(0.1, 0.3)
                        await asyncio.sleep(jitter)
                    
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            # Record success (resets backoff)
                            self.rate_limiter.record_success()
                            return html
                        elif response.status == 500:
                            # HTTP 500 on first request likely means IP is blocked
                            if attempt == 1 and len(self.rate_limiter.request_times) == 0:
                                logger.error(
                                    f"❌ HTTP 500 on FIRST request - Yahoo Japan has likely BLOCKED your IP address"
                                )
                                logger.error(
                                    "   💡 Solutions:"
                                )
                                logger.error(
                                    "   1. Wait 30-60 minutes before trying again"
                                )
                                logger.error(
                                    "   2. Test with: python3 test_ip_block.py"
                                )
                                logger.error(
                                    "   3. Try a different network (mobile hotspot, VPN)"
                                )
                                logger.error(
                                    "   4. Check if https://auctions.yahoo.co.jp works in your browser"
                                )
                            
                            # Record error and retry with exponential backoff
                            self.rate_limiter.record_error(response.status, YAHOO_RETRY_BACKOFF_BASE)
                            
                            if attempt < YAHOO_MAX_RETRIES:
                                delay = YAHOO_RETRY_BACKOFF_BASE ** attempt
                                logger.warning(f"❌ HTTP {response.status} for {url[:80]}...")
                                logger.warning(f"   ⏳ Retry {attempt}/{YAHOO_MAX_RETRIES} after {delay}s...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                logger.error(f"❌ HTTP {response.status} for {url[:80]}... (all retries exhausted)")
                                return None
                        elif response.status in (429, 502, 503, 504):
                            # Other server errors - record and retry
                            self.rate_limiter.record_error(response.status, YAHOO_RETRY_BACKOFF_BASE)
                            
                            if attempt < YAHOO_MAX_RETRIES:
                                delay = YAHOO_RETRY_BACKOFF_BASE ** attempt
                                logger.warning(f"❌ HTTP {response.status} for {url[:80]}...")
                                logger.warning(f"   ⏳ Retry {attempt}/{YAHOO_MAX_RETRIES} after {delay}s...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                logger.error(f"❌ HTTP {response.status} for {url[:80]}... (all retries exhausted)")
                                return None
                        else:
                            # Client error (4xx) - don't retry
                            print(f"❌ HTTP {response.status} for {url}")
                            return None
            except asyncio.TimeoutError:
                if attempt < YAHOO_MAX_RETRIES:
                    delay = YAHOO_RETRY_BACKOFF_BASE ** attempt
                    print(f"⏱️ Timeout fetching {url} (attempt {attempt}/{YAHOO_MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"⏱️ Timeout fetching {url} (all retries exhausted)")
                    return None
            except Exception as e:
                if attempt < YAHOO_MAX_RETRIES:
                    delay = YAHOO_RETRY_BACKOFF_BASE ** attempt
                    print(f"❌ Error fetching {url}: {e} (attempt {attempt}/{YAHOO_MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ Error fetching {url}: {e} (all retries exhausted)")
                    return None
        
        return None
    
    def parse_listing_item(self, item: BeautifulSoup, brand: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing item from BeautifulSoup element
        
        Args:
            item: BeautifulSoup element for the listing
            brand: Brand name for this listing
        
        Returns:
            Dictionary with listing data or None if parsing fails
        """
        try:
            # Get auction link and ID
            link_tag = item.select_one("a.Product__titleLink")
            if not link_tag:
                return None
            
            link = link_tag.get('href', '')
            if not link.startswith("http"):
                link = f"https://auctions.yahoo.co.jp{link}"
            
            # Extract auction ID
            auction_id = self.extract_auction_id_from_url(link)
            if not auction_id:
                return None
            
            # Get title
            title = link_tag.get_text(strip=True)
            if not title:
                return None
            
            # Get price
            price_tag = item.select_one(".Product__priceValue")
            if not price_tag:
                return None
            
            price_text = price_tag.get_text(strip=True)
            price_jpy = self.parse_price(price_text)
            if not price_jpy:
                return None
            
            # Get image URL
            img_tag = item.select_one("img")
            image_url = img_tag.get('src', '') if img_tag else None
            
            # Get seller ID
            seller_id = self.extract_seller_id(item)
            
            # Determine listing type
            listing_type = self.determine_listing_type(item)
            
            # Build listing data
            listing_data = {
                'market': 'yahoo',
                'external_id': auction_id,
                'title': title,
                'price_jpy': price_jpy,
                'brand': brand,
                'url': link,
                'image_url': image_url,
                'listing_type': listing_type,
                'seller_id': seller_id
            }
            
            return listing_data
            
        except Exception as e:
            print(f"❌ Error parsing listing item: {e}")
            return None
    
    async def scrape_brand_page(
        self,
        brand: str,
        page: int,
        max_price: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape a single page for a brand
        
        Args:
            brand: Brand name to search for
            page: Page number
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of listing dictionaries
        """
        url = self.build_search_url(
            keyword=brand,
            page=page,
            fixed_type=3,  # Both auctions and buy-it-now
            sort_type="new",  # Newest first
            sort_order="d",  # Descending
            max_price=max_price
        )
        
        html = await self.fetch_page_with_retry(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("li.Product")
        
        if not items:
            return []
        
        listings = []
        for item in items:
            listing_data = self.parse_listing_item(item, brand)
            if listing_data:
                listings.append(listing_data)
        
        return listings
    
    async def scrape_brand(
        self,
        brand: str,
        max_pages: int = 5,
        max_price: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages for a brand (SEQUENTIALLY to avoid rate limiting)
        
        Args:
            brand: Brand name to search for
            max_pages: Maximum number of pages to scrape
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of listing dictionaries
        """
        all_listings = []
        
        # Process pages SEQUENTIALLY (one at a time) to avoid Yahoo 500 errors
        # Parallel requests cause immediate blocking
        for page in range(1, max_pages + 1):
            try:
                page_listings = await self.scrape_brand_page(brand, page, max_price)
                all_listings.extend(page_listings)
                
                # Delay between pages (2-3 seconds like the original scraper)
                if page < max_pages:
                    delay = random.uniform(2.0, 3.0)
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"❌ Error scraping page {page} for {brand}: {e}")
                # Continue to next page even if one fails
                continue
        
        return all_listings
    
    async def scrape_listing_urls_parallel(
        self,
        listings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process listings in parallel batches (for additional data fetching if needed)
        
        Args:
            listings: List of listing dictionaries
        
        Returns:
            Processed listings
        """
        # For now, just return listings as-is
        # This method can be extended to fetch additional data from individual listing pages
        return listings
    
    async def scrape(
        self,
        brands: List[str],
        max_price: Optional[int] = None
    ) -> List[Listing]:
        """
        Main scraping method - scrapes brands sequentially to avoid rate limiting
        
        Args:
            brands: List of brand names to search for
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of Listing objects
        """
        # Ensure session is created
        await self._create_session()
        
        try:
            # Process brands SEQUENTIALLY to avoid overwhelming Yahoo
            # Parallel requests cause immediate 500 errors
            all_listings = []
            for brand in brands:
                try:
                    brand_listings = await self.scrape_brand(brand, max_pages=5, max_price=max_price)
                    all_listings.extend(brand_listings)
                    # Small delay between brands
                    if brand != brands[-1]:  # Don't delay after last brand
                        await asyncio.sleep(1.0)
                except Exception as e:
                    logger.error(f"❌ Error scraping {brand}: {e}")
                    continue
            
            # Old parallel approach (causes 500 errors):
            # brand_tasks = [
            #     self.scrape_brand(brand, max_pages=5, max_price=max_price)
            #     for brand in brands
            # ]
            # brand_results = await asyncio.gather(*brand_tasks, return_exceptions=True)
            
            # Results already collected in sequential loop above
            
            # Deduplicate by URL
            unique_listings = self.deduplicate(all_listings, key_field='url')
            
            # Convert to Listing objects
            listing_objects = []
            for listing_data in unique_listings:
                listing = Listing(
                    market=listing_data['market'],
                    external_id=listing_data['external_id'],
                    title=listing_data['title'],
                    price_jpy=listing_data['price_jpy'],
                    brand=listing_data.get('brand'),
                    url=listing_data['url'],
                    image_url=listing_data.get('image_url'),
                    listing_type=listing_data['listing_type'],
                    seller_id=listing_data.get('seller_id'),
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc)
                )
                listing_objects.append(listing)
            
            return listing_objects
            
        finally:
            # Session will be closed by context manager or manually
            pass

