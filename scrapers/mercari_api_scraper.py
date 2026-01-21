"""
Async Mercari API scraper - Direct API access (no Playwright!)
Uses aiohttp to make POST requests to Mercari's internal API
10x faster than Playwright version with better coverage

NOTE: This API requires authentication. If you get 401 errors:
1. Run: python v2/debug_mercari_api.py to see what headers/cookies are needed
2. Check your browser's Network tab when the API call succeeds
3. Look for auth tokens in cookies or Authorization headers
4. Update the _get_session_cookies() method to extract the correct token
"""
import asyncio
import aiohttp
import uuid
import random
import logging
import time
import base64
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

# DPoP token generation
try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    import jwt
    DPOP_AVAILABLE = True
except ImportError:
    DPOP_AVAILABLE = False
    # Logger not yet defined, will log later
    pass

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
    from .rate_limiter import RateLimiter
except ImportError:
    from scrapers.base import BaseScraper
    from scrapers.rate_limiter import RateLimiter

from config import (
    MERCARI_MAX_REQUESTS_PER_MINUTE,
    MERCARI_MIN_DELAY_BETWEEN_REQUESTS,
    MERCARI_MAX_RETRIES,
    MERCARI_RETRY_BACKOFF_BASE,
    MERCARI_TIMEOUT,
    MIN_PAGES,
    MAX_PAGES,
    STOP_ON_DUPLICATE,
)

from models import Listing

try:
    from database import listing_exists as listing_exists_async
except ImportError:
    from database import listing_exists as listing_exists_async

# Alias for cleaner code
listing_exists = listing_exists_async


class MercariAPIScraper(BaseScraper):
    """Async Mercari API scraper using direct API calls (no browser needed!)"""
    
    # Mercari API endpoint
    API_ENDPOINT = "https://api.mercari.jp/v2/entities:search"
    
    # Base headers for Mercari website
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    def _get_api_headers(self, device_uuid: str) -> Dict[str, str]:
        """
        Get API request headers, including DPoP token
        
        Args:
            device_uuid: Device UUID for DPoP token generation
        
        Returns:
            Dictionary of headers for API request
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
            "X-Platform": "web",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://jp.mercari.com",
            "Referer": "https://jp.mercari.com/",
            "Accept-Language": "ja",
            "Sec-CH-UA": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "X-Country-Code": "US",
        }
        
        # Generate and add DPoP token
        dpop_token = self._generate_dpop_token(device_uuid)
        if dpop_token:
            headers["DPoP"] = dpop_token
        else:
            logger.warning("⚠️  Could not generate DPoP token - request may fail")
        
        return headers
    
    def __init__(self):
        super().__init__()
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookies: Optional[Dict[str, str]] = None
        self.auth_token: Optional[str] = None
        # DPoP key pair (generated once, reused for all requests)
        self.dpop_private_key = None
        self.dpop_public_key_jwk = None
        if DPOP_AVAILABLE:
            self._generate_dpop_key_pair()
        else:
            logger.warning("⚠️  DPoP token generation requires: pip install pyjwt cryptography")
        # Initialize rate limiter for Mercari API domain
        self.rate_limiter = RateLimiter(
            domain="api.mercari.jp",
            max_requests_per_minute=MERCARI_MAX_REQUESTS_PER_MINUTE
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
        """Create aiohttp session with connection pooling and get cookies"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                ttl_dns_cache=300
            )
            timeout = aiohttp.ClientTimeout(
                total=MERCARI_TIMEOUT,
                connect=5
            )
            # Create session without default headers (we'll set them per request)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
            # Get cookies by visiting the Mercari site first (will be refreshed per brand if needed)
            await self._get_session_cookies("test")
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self.cookies = None
    
    async def _get_session_cookies(self, keyword: str = "test"):
        """
        Visit Mercari website to get session cookies needed for API authentication
        """
        try:
            # Visit the Mercari homepage first
            logger.debug("🍪 Getting session cookies from Mercari website...")
            async with self.session.get(
                "https://jp.mercari.com",
                headers=self.BASE_HEADERS,
                allow_redirects=True
            ) as response:
                if response.status == 200:
                    logger.debug("   ✅ Visited homepage")
            
            # Then visit the search page (with a query) to establish search session
            import urllib.parse
            search_url = f"https://jp.mercari.com/search?keyword={urllib.parse.quote(keyword)}"
            async with self.session.get(
                search_url,
                headers=self.BASE_HEADERS,
                allow_redirects=True
            ) as response:
                if response.status == 200:
                    # aiohttp automatically stores cookies in session.cookie_jar
                    # Extract cookies for manual use if needed
                    cookies_dict = {}
                    for cookie in self.session.cookie_jar:
                        cookies_dict[cookie.key] = cookie.value
                    self.cookies = cookies_dict
                    logger.debug(f"✅ Got {len(cookies_dict)} cookies from Mercari search page")
                    
                    # Look for auth token in cookies (common names)
                    auth_token_names = [
                        'auth_token', 'authToken', 'auth-token',
                        'mercari_auth', 'mercariAuth', 'mercari-auth',
                        'session_token', 'sessionToken', 'session-token',
                        'access_token', 'accessToken', 'access-token',
                        '_mercari_session', 'mercari_session', 'mercariSession',
                        'token', 'Token', 'TOKEN',
                        'authorization', 'Authorization', 'AUTHORIZATION'
                    ]
                    
                    for cookie_name in cookies_dict.keys():
                        if any(auth_name.lower() in cookie_name.lower() for auth_name in auth_token_names):
                            self.auth_token = cookies_dict[cookie_name]
                            logger.info(f"🔑 Found potential auth token in cookie: {cookie_name}")
                            break
                    
                    # Log all cookie names for debugging
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"   Cookie names: {list(cookies_dict.keys())}")
                else:
                    logger.warning(f"⚠️  Failed to get cookies from search page: HTTP {response.status}")
                    self.cookies = {}
        except Exception as e:
            logger.warning(f"⚠️  Error getting cookies: {e}")
            self.cookies = {}
    
    def _generate_search_session_id(self) -> str:
        """Generate random searchSessionId (UUID format without dashes)"""
        return uuid.uuid4().hex
    
    def _generate_device_uuid(self) -> str:
        """Generate random laplaceDeviceUuid (UUID format with dashes)"""
        return str(uuid.uuid4())
    
    def _generate_dpop_key_pair(self):
        """Generate ES256 key pair for DPoP tokens"""
        if not DPOP_AVAILABLE:
            return
        
        try:
            # Generate P-256 (ES256) private key
            self.dpop_private_key = ec.generate_private_key(
                ec.SECP256R1(),  # P-256 curve
                default_backend()
            )
            
            # Get public key
            public_key = self.dpop_private_key.public_key()
            
            # Serialize public key to JWK format
            public_numbers = public_key.public_numbers()
            
            # Convert to JWK format (RFC 7517)
            # P-256 uses specific curve parameters
            # Calculate the number of bytes needed (P-256 uses 256 bits = 32 bytes)
            x_int = public_numbers.x
            y_int = public_numbers.y
            
            # Convert to bytes (big-endian, exactly 32 bytes for P-256)
            x_bytes = x_int.to_bytes((x_int.bit_length() + 7) // 8, 'big')
            y_bytes = y_int.to_bytes((y_int.bit_length() + 7) // 8, 'big')
            
            # Pad to 32 bytes if needed (P-256 coordinates are exactly 32 bytes)
            x_bytes = x_bytes.rjust(32, b'\x00')
            y_bytes = y_bytes.rjust(32, b'\x00')
            
            # Base64url encode without padding
            x_b64 = base64.urlsafe_b64encode(x_bytes).decode('utf-8').rstrip('=')
            y_b64 = base64.urlsafe_b64encode(y_bytes).decode('utf-8').rstrip('=')
            
            self.dpop_public_key_jwk = {
                "crv": "P-256",
                "kty": "EC",
                "x": x_b64,
                "y": y_b64
            }
            
            logger.debug("✅ Generated DPoP key pair")
        except Exception as e:
            logger.warning(f"⚠️  Failed to generate DPoP key pair: {e}")
            self.dpop_private_key = None
            self.dpop_public_key_jwk = None
    
    def _generate_dpop_token(self, device_uuid: str) -> Optional[str]:
        """
        Generate DPoP (Demonstrating Proof-of-Possession) JWT token
        
        Args:
            device_uuid: Device UUID (laplaceDeviceUuid)
        
        Returns:
            DPoP token string or None if generation fails
        """
        if not DPOP_AVAILABLE or not self.dpop_private_key:
            return None
        
        try:
            # Current timestamp
            iat = int(time.time())
            
            # Generate unique JWT ID
            jti = str(uuid.uuid4())
            
            # DPoP header
            header = {
                "typ": "dpop+jwt",
                "alg": "ES256",
                "jwk": self.dpop_public_key_jwk
            }
            
            # DPoP payload
            payload = {
                "iat": iat,
                "jti": jti,
                "htu": self.API_ENDPOINT,  # HTTP URI
                "htm": "POST",  # HTTP method
                "uuid": device_uuid
            }
            
            # Sign JWT with private key
            token = jwt.encode(
                payload,
                self.dpop_private_key,
                algorithm="ES256",
                headers=header
            )
            
            return token
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to generate DPoP token: {e}")
            return None
    
    def _build_request_payload(
        self,
        keyword: str,
        page_token: str = "",
        price_max: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build API request payload
        
        Args:
            keyword: Brand name to search for
            page_token: Pagination token (empty for first page)
            price_max: Optional maximum price filter (JPY)
        
        Returns:
            Request payload dictionary
        """
        payload = {
            "userId": "",
            "pageSize": 120,
            "pageToken": page_token,
            "searchSessionId": self._generate_search_session_id(),
            "source": "BaseSerp",
            "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
            "thumbnailTypes": [],
            "searchCondition": {
                "keyword": keyword,
                "excludeKeyword": "",
                "sort": "SORT_CREATED_TIME",
                "order": "ORDER_DESC",
                "status": [],
                "sizeId": [],
                "categoryId": [],
                "brandId": [],
                "sellerId": [],
                "priceMin": 0,
                "priceMax": price_max if price_max else 0,
                "itemConditionId": [],
                "shippingPayerId": [],
                "shippingFromArea": [],
                "shippingMethod": [],
                "colorId": [],
                "hasCoupon": False,
                "attributes": [],
                "itemTypes": [],
                "skuIds": [],
                "shopIds": [],
                "excludeShippingMethodIds": []
            },
            "serviceFrom": "suruga",
            "withItemBrand": True,
            "withItemSize": False,
            "withItemPromotions": True,
            "withItemSizes": True,
            "withShopname": False,
            "useDynamicAttribute": True,
            "withSuggestedItems": True,
            "withOfferPricePromotion": True,
            "withProductSuggest": True,
            "withParentProducts": False,
            "withProductArticles": True,
            "withSearchConditionId": False,
            "withAuction": True,
            "laplaceDeviceUuid": self._generate_device_uuid()
        }
        return payload
    
    async def _fetch_page_with_retry(
        self,
        keyword: str,
        page_token: str = "",
        price_max: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch API page with rate limiting, exponential backoff retry logic
        
        Args:
            keyword: Brand name to search for
            page_token: Pagination token (empty for first page)
            price_max: Optional maximum price filter (JPY)
        
        Returns:
            JSON response data or None if all retries fail
        """
        if self.session is None:
            await self._create_session()
        
        payload = self._build_request_payload(keyword, page_token, price_max)
        device_uuid = payload.get("laplaceDeviceUuid", "")
        
        for attempt in range(1, MERCARI_MAX_RETRIES + 1):
            try:
                # For first request, add initial delay
                if attempt == 1 and len(self.rate_limiter.request_times) == 0:
                    logger.info("⏳ Initial delay before first request (2s)...")
                    await asyncio.sleep(2.0)
                
                # Acquire rate limiter permission (waits if needed, enforces min delay)
                await self.rate_limiter.acquire(min_delay=MERCARI_MIN_DELAY_BETWEEN_REQUESTS)
                
                # Add small random jitter (0.1-0.3s) to avoid synchronized requests
                if attempt == 1:
                    jitter = random.uniform(0.1, 0.3)
                    await asyncio.sleep(jitter)
                
                # Get headers with DPoP token
                api_headers = self._get_api_headers(device_uuid)
                
                async with self.session.post(
                    self.API_ENDPOINT,
                    json=payload,
                    headers=api_headers
                ) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        # Record success (resets backoff)
                        self.rate_limiter.record_success()
                        return json_data
                    elif response.status == 401:
                        # Get error response body for debugging
                        try:
                            error_body = await response.text()
                            logger.warning(f"⚠️  HTTP 401 - Authentication failed")
                            logger.warning(f"   Response: {error_body[:500]}")
                        except Exception:
                            pass
                        
                        # Try refreshing cookies and generating new searchSessionId
                        if attempt == 1:
                            logger.info("   🔄 Refreshing session cookies...")
                            await self._get_session_cookies(keyword)
                        
                        payload["searchSessionId"] = self._generate_search_session_id()
                        payload["laplaceDeviceUuid"] = self._generate_device_uuid()
                        
                        if attempt < MERCARI_MAX_RETRIES:
                            delay = MERCARI_RETRY_BACKOFF_BASE ** attempt
                            logger.info(f"   ⏳ Retry {attempt}/{MERCARI_MAX_RETRIES} after {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ HTTP 401 for {keyword} (all retries exhausted)")
                            logger.error(f"   💡 The API may require additional authentication or the endpoint may have changed")
                            return None
                    elif response.status in (429, 500, 502, 503, 504):
                        # Server errors - record and retry
                        self.rate_limiter.record_error(response.status, MERCARI_RETRY_BACKOFF_BASE)
                        
                        if attempt < MERCARI_MAX_RETRIES:
                            delay = MERCARI_RETRY_BACKOFF_BASE ** attempt
                            logger.warning(f"❌ HTTP {response.status} for {keyword}...")
                            logger.warning(f"   ⏳ Retry {attempt}/{MERCARI_MAX_RETRIES} after {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ HTTP {response.status} for {keyword}... (all retries exhausted)")
                            return None
                    else:
                        # Client error (4xx) - don't retry
                        error_text = await response.text()
                        logger.error(f"❌ HTTP {response.status} for {keyword}: {error_text[:200]}")
                        return None
            except asyncio.TimeoutError:
                if attempt < MERCARI_MAX_RETRIES:
                    delay = MERCARI_RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"⏱️ Timeout fetching {keyword} (attempt {attempt}/{MERCARI_MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"⏱️ Timeout fetching {keyword} (all retries exhausted)")
                    return None
            except Exception as e:
                if attempt < MERCARI_MAX_RETRIES:
                    delay = MERCARI_RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"❌ Error fetching {keyword}: {e} (attempt {attempt}/{MERCARI_MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Error fetching {keyword}: {e} (all retries exhausted)")
                    return None
        
        return None
    
    def _parse_api_item(self, item: Dict[str, Any], brand: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single item from API response
        
        Args:
            item: Item data from API response
            brand: Brand name for this listing
        
        Returns:
            Listing dictionary or None if parsing fails
        """
        try:
            # Extract item ID
            item_id = item.get("id")
            if not item_id:
                return None
            
            # Extract title
            title = item.get("name", "").strip()
            if not title:
                return None
            
            # Extract price (comes as string, convert to int)
            price_str = item.get("price", "")
            if not price_str:
                return None
            
            try:
                price_jpy = int(price_str)
            except (ValueError, TypeError):
                return None
            
            # Extract image URL (first thumbnail)
            thumbnails = item.get("thumbnails", [])
            image_url = thumbnails[0] if thumbnails else None
            
            # Extract brand from itemBrand if available
            # Note: itemBrand can be null, so check for that
            item_brand = item.get("itemBrand")
            if item_brand and isinstance(item_brand, dict):
                brand_name = item_brand.get("name") or brand
            else:
                # itemBrand is null or missing, use the search brand
                brand_name = brand
            
            # Extract seller ID
            seller_id = item.get("sellerId")
            if seller_id:
                seller_id = str(seller_id)
            else:
                seller_id = None
            
            # Construct URL
            url = f"https://jp.mercari.com/item/{item_id}"
            
            # Mercari only has fixed price listings (no auctions)
            listing_type = "fixed"
            
            # Build listing data
            listing_data = {
                'market': 'mercari',
                'external_id': str(item_id),
                'title': title,
                'price_jpy': price_jpy,
                'brand': brand_name,
                'url': url,
                'image_url': image_url,
                'listing_type': listing_type,
                'seller_id': seller_id
            }
            
            return listing_data
            
        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None
    
    async def scrape_brand_page(
        self,
        brand: str,
        page_token: str = "",
        max_price: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Scrape a single page for a brand
        
        Args:
            brand: Brand name to search for
            page_token: Pagination token (empty for first page)
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            Tuple of (list of listing dictionaries, next_page_token)
        """
        json_data = await self._fetch_page_with_retry(brand, page_token, max_price)
        if not json_data:
            return [], None
        
        # Extract items from response
        items = []
        try:
            # The API returns items at the top level, not in a "data" key
            # Response structure: { "meta": {...}, "items": [...], ... }
            items = json_data.get("items", [])
            
            if not isinstance(items, list):
                logger.warning(f"⚠️  'items' is not a list: {type(items)}")
                return [], None
            
            logger.info(f"   📦 Found {len(items)} items in response")
            
        except (AttributeError, KeyError) as e:
            logger.warning(f"⚠️  Unexpected API response structure for {brand}: {e}")
            import json as json_module
            logger.warning(f"   Response keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
            return [], None
        
        if not items:
            logger.warning(f"⚠️  No items in response for {brand}")
            return [], None
        
        # Extract next page token for pagination
        # The API returns meta at the top level: { "meta": { "nextPageToken": "v1:1", ... } }
        next_page_token = json_data.get("meta", {}).get("nextPageToken")
        
        # Parse items
        listings = []
        for item in items:
            listing_data = self._parse_api_item(item, brand)
            if listing_data:
                listings.append(listing_data)
        
        return listings, next_page_token
    
    async def scrape_brand(
        self,
        brand: str,
        max_pages: int = MAX_PAGES,
        max_price: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages for a brand using pagination
        
        Args:
            brand: Brand name to search for
            max_pages: Maximum number of pages to scrape
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of listing dictionaries
        """
        all_listings: List[Dict[str, Any]] = []
        page_token = ""
        page_num = 1
        pages_scraped = 0
        found_existing = False
        
        # Ensure we always scrape at least MIN_PAGES (but never more than max_pages)
        effective_max_pages = max(min(max_pages, MAX_PAGES), MIN_PAGES)
        
        while page_num <= effective_max_pages:
            try:
                logger.info(f"📄 Scraping page {page_num}/{max_pages} for {brand}...")
                page_listings, next_page_token = await self.scrape_brand_page(
                    brand, page_token, max_price
                )
                
                pages_scraped += 1
                page_count = len(page_listings)
                logger.info(f"   ✅ Page {page_num}: {page_count} listings (expected: 120)")
                
                if not page_listings:
                    logger.info(f"ℹ️  No listings on page {page_num} for {brand}")
                else:
                    # Smart pagination: stop when we hit already-seen listings
                    for listing_data in page_listings:
                        external_id = listing_data.get("external_id")
                        if STOP_ON_DUPLICATE and external_id:
                            # Check if listing exists in database (async)
                            exists = await listing_exists(external_id, "mercari")
                            if exists:
                                logger.info(
                                    f"Stopped at page {page_num} for {brand} (found existing listings)"
                                )
                                found_existing = True
                                break
                        all_listings.append(listing_data)
                    
                    if not found_existing:
                        logger.info(
                            f"Page {page_num} for {brand}: {len(page_listings)} listings, all new so far"
                        )
                
                # Check if there's a next page
                if not next_page_token:
                    logger.info(f"   ℹ️  No more pages available (reached end of results)")
                    break
                
                # If we found an existing listing, stop immediately for this brand
                if found_existing:
                    break
                
                page_token = next_page_token
                page_num += 1
                
                # Small delay between pages
                if page_num <= effective_max_pages:
                    delay = random.uniform(0.5, 1.0)
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"❌ Error scraping page {page_num} for {brand}: {e}")
                # Continue to next page even if one fails
                page_num += 1
                continue
        
        # Log if we hit the safety limit without encountering any existing listings
        if not found_existing and pages_scraped >= effective_max_pages:
            logger.info(f"Scraped all {effective_max_pages} pages for {brand} (all new)")
        
        total_expected = pages_scraped * 120
        total_found = len(all_listings)
        coverage = (total_found / total_expected * 100) if total_expected > 0 else 0
        logger.info(
            f"📊 {brand}: {total_found} listings from {pages_scraped} page(s) "
            f"(expected: {total_expected}, coverage: {coverage:.1f}%)"
        )
        
        return all_listings
    
    async def scrape(
        self,
        brands: List[str],
        max_price: Optional[int] = None
    ) -> List[Listing]:
        """
        Main scraping method - scrapes brands sequentially
        
        Args:
            brands: List of brand names to search for
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of Listing objects
        """
        # Ensure session is created
        await self._create_session()
        
        try:
            # Process brands SEQUENTIALLY to avoid overwhelming API
            all_listings: List[Dict[str, Any]] = []
            pages_per_brand = {}
            for brand in brands:
                try:
                    before_count = len(all_listings)
                    brand_listings = await self.scrape_brand(
                        brand, max_pages=MAX_PAGES, max_price=max_price
                    )
                    after_count = len(all_listings) + len(brand_listings)
                    # We know Mercari returns up to 120 items/page
                    estimated_pages = max(1, min(MAX_PAGES, (len(brand_listings) + 119) // 120))
                    pages_per_brand[brand] = estimated_pages
                    all_listings.extend(brand_listings)
                    logger.info(
                        f"Brand {brand}: {after_count - before_count} new listings collected in this run"
                    )
                    # Small delay between brands
                    if brand != brands[-1]:  # Don't delay after last brand
                        await asyncio.sleep(1.0)
                except Exception as e:
                    logger.error(f"❌ Error scraping {brand}: {e}")
                    continue

            # Track average pages per brand for this run
            if pages_per_brand:
                total_pages = sum(pages_per_brand.values())
                avg_pages = total_pages / len(pages_per_brand)
                logger.info(
                    f"📊 Mercari average pages per brand this run: {avg_pages:.2f} "
                    f"(min={min(pages_per_brand.values())}, max={max(pages_per_brand.values())})"
                )
            
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

