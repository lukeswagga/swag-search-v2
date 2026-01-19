"""
Async Yahoo Japan scraper - 10x faster with parallel processing
Uses aiohttp + BeautifulSoup for async HTML parsing
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .base import BaseScraper
from ..config import (
    YAHOO_SEARCH_URL,
    YAHOO_TIMEOUT,
    YAHOO_CONNECT_TIMEOUT,
    YAHOO_MAX_RETRIES,
    YAHOO_RETRY_BACKOFF_BASE,
    YAHOO_RATE_LIMIT_DELAY,
    MAX_CONCURRENT_REQUESTS,
    BATCH_SIZE,
    DEFAULT_HEADERS
)
from ..models import Listing


class YahooScraper(BaseScraper):
    """Async Yahoo Japan scraper with parallel processing"""
    
    def __init__(self):
        super().__init__()
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session with connection pooling"""
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
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=DEFAULT_HEADERS
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
            'fixed': str(fixed_type),
            'is_postage_mode': '1',
            'dest_pref_code': '13',  # Tokyo prefecture for shipping
            'b': str(start_position),
            'n': str(page_size)
        }
        
        # Add price filter if specified
        if max_price:
            params['price_range'] = f'0,{max_price}'
        
        # Add sorting parameters
        if sort_type == "end":
            params['s1'] = 'end'
            params['o1'] = sort_order
        elif sort_type == "new":
            params['s1'] = 'new'
            params['o1'] = sort_order
        elif sort_type == "price":
            params['s1'] = 'cbids'
            params['o1'] = sort_order
        
        # Build URL with proper encoding
        param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
        return f"{YAHOO_SEARCH_URL}?{param_string}"
    
    async def fetch_page_with_retry(self, url: str) -> Optional[str]:
        """
        Fetch page with exponential backoff retry logic
        
        Args:
            url: URL to fetch
        
        Returns:
            HTML content or None if all retries fail
        """
        if self.session is None:
            await self._create_session()
        
        for attempt in range(1, YAHOO_MAX_RETRIES + 1):
            try:
                async with self._semaphore:  # Rate limiting
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            # Small delay to avoid overwhelming Yahoo
                            await asyncio.sleep(YAHOO_RATE_LIMIT_DELAY)
                            return html
                        elif response.status >= 500:
                            # Server error - retry with exponential backoff
                            if attempt < YAHOO_MAX_RETRIES:
                                delay = YAHOO_RETRY_BACKOFF_BASE ** attempt
                                print(f"❌ HTTP {response.status} for {url}")
                                print(f"   ⏳ Retry {attempt}/{YAHOO_MAX_RETRIES} after {delay}s...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                print(f"❌ HTTP {response.status} for {url} (all retries exhausted)")
                                return None
                        else:
                            # Client error - don't retry
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
        Scrape multiple pages for a brand (parallel page fetching)
        
        Args:
            brand: Brand name to search for
            max_pages: Maximum number of pages to scrape
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of listing dictionaries
        """
        # Create tasks for all pages
        tasks = [
            self.scrape_brand_page(brand, page, max_price)
            for page in range(1, max_pages + 1)
        ]
        
        # Fetch all pages in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter out errors
        all_listings = []
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Error scraping page for {brand}: {result}")
                continue
            all_listings.extend(result)
        
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
        Main scraping method - scrapes all brands in parallel
        
        Args:
            brands: List of brand names to search for
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of Listing objects
        """
        # Ensure session is created
        await self._create_session()
        
        try:
            # Scrape all brands in parallel
            brand_tasks = [
                self.scrape_brand(brand, max_pages=5, max_price=max_price)
                for brand in brands
            ]
            
            brand_results = await asyncio.gather(*brand_tasks, return_exceptions=True)
            
            # Flatten and process results
            all_listings = []
            for i, result in enumerate(brand_results):
                if isinstance(result, Exception):
                    print(f"❌ Error scraping {brands[i]}: {result}")
                    continue
                all_listings.extend(result)
            
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

