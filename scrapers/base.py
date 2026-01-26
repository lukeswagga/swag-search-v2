"""
Abstract base class for all scrapers
Provides common functionality for parsing, rate limiting, and deduplication
"""
from abc import ABC, abstractmethod
import re
from typing import List, Optional, Dict, Any
from datetime import datetime


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self):
        self.seen_urls = set()  # Track seen URLs to prevent duplicates
    
    @abstractmethod
    async def scrape(self, brands: List[str], max_price: Optional[int] = None) -> List[Any]:
        """
        Main scraping method - must be implemented by subclasses
        
        Args:
            brands: List of brand names to search for
            max_price: Optional maximum price filter (JPY)
        
        Returns:
            List of Listing objects or dicts
        """
        pass
    
    def parse_price(self, price_text: str) -> Optional[int]:
        """
        Extract numeric price from price text
        
        Args:
            price_text: Price text from HTML (e.g., "¥12,000", "12,000円")
        
        Returns:
            Price as integer (JPY) or None if parsing fails
        """
        if not price_text:
            return None
        
        # Remove currency symbols and extract numbers
        price_match = re.search(r'([\d,]+)', price_text.replace(',', ''))
        if price_match:
            try:
                return int(price_match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None
    
    def extract_brand(self, title: str, brand_list: List[str]) -> Optional[str]:
        """
        Extract brand name from listing title
        
        Args:
            title: Listing title
            brand_list: List of brand names to search for
            
        Returns:
            Brand name if found, None otherwise
        """
        if not title or not brand_list:
            return None
        
        title_lower = title.lower()
        
        # Check each brand (case-insensitive)
        for brand in brand_list:
            if brand.lower() in title_lower:
                return brand
        
        return None
    
    def deduplicate(self, listings: List[Any], key_field: str = 'url') -> List[Any]:
        """
        Remove duplicate listings based on a key field
        
        Args:
            listings: List of listing objects/dicts
            key_field: Field name to use for deduplication (default: 'url')
        
        Returns:
            Deduplicated list of listings
        """
        seen = set()
        unique_listings = []
        
        for listing in listings:
            # Handle both dict and object access
            if isinstance(listing, dict):
                key = listing.get(key_field)
            else:
                key = getattr(listing, key_field, None)
            
            if key and key not in seen:
                seen.add(key)
                unique_listings.append(listing)
        
        return unique_listings
    
    def extract_auction_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract auction ID from Yahoo Japan URL
        
        Args:
            url: Yahoo auction URL
        
        Returns:
            Auction ID (with 'u' prefix for ZenMarket) or None
        """
        if not url:
            return None
        
        try:
            auction_id = None
            
            # Method 1: Extract from /auction/ path
            if "/auction/" in url:
                auction_id = url.split("/auction/")[-1].split("?")[0]
            
            # Method 2: Extract from aID parameter
            elif "aID=" in url:
                auction_id = url.split("aID=")[-1].split("&")[0]
            
            # Method 3: Extract from URL segments
            else:
                url_parts = url.split("/")
                for part in reversed(url_parts):
                    if part and not part.startswith("?") and len(part) > 5:
                        auction_id = part.split("?")[0]
                        break
            
            if auction_id:
                # Clean up the auction ID - keep the 'u' prefix for ZenMarket
                auction_id = auction_id.strip()
                
                # Ensure the auction ID has the 'u' prefix for ZenMarket
                if not auction_id.startswith('u') and auction_id.isdigit():
                    auction_id = f"u{auction_id}"
                
                return auction_id
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting auction ID from {url}: {e}")
            return None
    
    def extract_seller_id(self, item_html: Any) -> Optional[str]:
        """
        Extract seller ID from listing HTML element
        
        Args:
            item_html: BeautifulSoup element for the listing
        
        Returns:
            Seller ID or None
        """
        try:
            seller_link = item_html.select_one("a[href*='sellerID']")
            if seller_link:
                href = seller_link.get('href', '')
                seller_match = re.search(r'sellerID=([^&]+)', href)
                if seller_match:
                    return seller_match.group(1)
            return None
        except Exception:
            return None
    
    def determine_listing_type(self, item_html: Any) -> str:
        """
        Determine if listing is auction or buy_it_now
        
        Args:
            item_html: BeautifulSoup element for the listing
        
        Returns:
            "auction" or "buy_it_now"
        """
        try:
            # Check for fixed price indicators in various ways
            # Method 1: Check for fixed price class
            fixed_price_indicators = item_html.select(".Product__priceType--fixed")
            if fixed_price_indicators:
                return "buy_it_now"
            
            # Method 2: Check for "即決" (immediate purchase) text
            text_content = item_html.get_text()
            if "即決" in text_content or "即購入" in text_content:
                return "buy_it_now"
            
            # Method 3: Check URL for fixed price indicators
            link_tag = item_html.select_one("a.Product__titleLink")
            if link_tag:
                href = link_tag.get('href', '')
                if 'fixed' in href.lower() or 'buy' in href.lower():
                    return "buy_it_now"
            
            # Default to auction
            return "auction"
        except Exception:
            return "auction"

