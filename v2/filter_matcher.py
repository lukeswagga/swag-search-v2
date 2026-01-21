"""
Filter matcher for matching listings against user-defined filters
"""
import json
import logging
from typing import List, Dict, Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Listing, UserFilter
else:
    try:
        from .models import Listing, UserFilter
    except ImportError:
        from models import Listing, UserFilter

logger = logging.getLogger(__name__)


class FilterMatcher:
    """
    Matches listings against user-defined filters
    
    Matching logic:
    - listing.brand in filter.brands (case-insensitive, partial match)
    - listing.price_jpy >= filter.price_min (if set)
    - listing.price_jpy <= filter.price_max (if set)
    - listing.market in filter.markets
    - If filter.keywords: any keyword in listing.title (case-insensitive)
    - All conditions must match (AND logic)
    """
    
    def __init__(self, database):
        """
        Initialize filter matcher
        
        Args:
            database: Database module with filter operations
        """
        self.db = database
    
    def _parse_json_field(self, field_value: Optional[str]) -> List[str]:
        """
        Parse JSON array field from database
        
        Args:
            field_value: JSON string or None
            
        Returns:
            List of strings, empty list if None or invalid
        """
        if not field_value:
            return []
        
        try:
            parsed = json.loads(field_value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if item]
            elif isinstance(parsed, str):
                # Handle comma-separated string
                return [item.strip() for item in parsed.split(',') if item.strip()]
            else:
                return []
        except (json.JSONDecodeError, TypeError):
            # Try comma-separated string parsing
            try:
                return [item.strip() for item in field_value.split(',') if item.strip()]
            except:
                return []
    
    def _parse_markets(self, markets_field: Optional[str]) -> List[str]:
        """
        Parse markets field (comma-separated string)
        
        Args:
            markets_field: Comma-separated markets string or None
            
        Returns:
            List of market names (lowercased)
        """
        if not markets_field:
            return []
        
        markets = [m.strip().lower() for m in markets_field.split(',') if m.strip()]
        return markets
    
    def _brand_matches(self, listing_brand: Optional[str], filter_brands: List[str]) -> bool:
        """
        Check if listing brand matches any filter brand (case-insensitive, partial match)
        
        Args:
            listing_brand: Listing brand name (can be None)
            filter_brands: List of filter brand names
            
        Returns:
            True if matches, False otherwise
        """
        if not filter_brands:
            return True  # No brand filter means match all
        
        if not listing_brand:
            return False  # Listing has no brand, can't match
        
        listing_brand_lower = listing_brand.lower().strip()
        
        for filter_brand in filter_brands:
            filter_brand_lower = filter_brand.lower().strip()
            # Partial match: check if filter brand is in listing brand or vice versa
            if filter_brand_lower in listing_brand_lower or listing_brand_lower in filter_brand_lower:
                return True
        
        return False
    
    def _price_matches(self, listing_price: int, price_min: Optional[float], price_max: Optional[float]) -> bool:
        """
        Check if listing price matches filter price range
        
        Args:
            listing_price: Listing price in JPY
            price_min: Minimum price (None means no minimum)
            price_max: Maximum price (None means no maximum)
            
        Returns:
            True if price is within range, False otherwise
        """
        if price_min is not None and listing_price < price_min:
            return False
        
        if price_max is not None and listing_price > price_max:
            return False
        
        return True
    
    def _market_matches(self, listing_market: str, filter_markets: List[str]) -> bool:
        """
        Check if listing market matches filter markets
        
        Args:
            listing_market: Listing market name
            filter_markets: List of filter market names
            
        Returns:
            True if matches, False otherwise
        """
        if not filter_markets:
            return True  # No market filter means match all
        
        listing_market_lower = listing_market.lower().strip()
        return listing_market_lower in filter_markets
    
    def _keywords_match(self, listing_title: str, filter_keywords: List[str]) -> bool:
        """
        Check if any filter keyword appears in listing title (case-insensitive)
        
        Args:
            listing_title: Listing title
            filter_keywords: List of keywords to search for
            
        Returns:
            True if any keyword matches, False otherwise
        """
        if not filter_keywords:
            return True  # No keywords means match all
        
        listing_title_lower = listing_title.lower()
        
        for keyword in filter_keywords:
            keyword_lower = keyword.lower().strip()
            if keyword_lower and keyword_lower in listing_title_lower:
                return True
        
        return False
    
    async def match_listing(self, listing: Listing, filter_obj: UserFilter) -> bool:
        """
        Check if a listing matches a single filter
        
        Args:
            listing: Listing object
            filter_obj: UserFilter object
            
        Returns:
            True if listing matches filter, False otherwise
        """
        # Parse filter fields
        filter_brands = self._parse_json_field(filter_obj.brands)
        filter_markets = self._parse_markets(filter_obj.markets)
        filter_keywords = self._parse_json_field(filter_obj.keywords)
        
        # Check all conditions (AND logic)
        
        # 1. Brand match
        if not self._brand_matches(listing.brand, filter_brands):
            return False
        
        # 2. Price range match
        if not self._price_matches(listing.price_jpy, filter_obj.price_min, filter_obj.price_max):
            return False
        
        # 3. Market match
        if not self._market_matches(listing.market, filter_markets):
            return False
        
        # 4. Keywords match
        if not self._keywords_match(listing.title, filter_keywords):
            return False
        
        # All conditions passed
        return True
    
    async def get_matches_for_listing(self, listing: Listing, filters: List[UserFilter]) -> List[UserFilter]:
        """
        Find all filters that match a single listing
        
        Args:
            listing: Listing object
            filters: List of UserFilter objects to check
            
        Returns:
            List of matching UserFilter objects
        """
        matching_filters = []
        
        for filter_obj in filters:
            if await self.match_listing(listing, filter_obj):
                matching_filters.append(filter_obj)
        
        return matching_filters
    
    async def get_matches_for_batch(self, listings: List[Listing], filters: List[UserFilter]) -> Dict[int, List[UserFilter]]:
        """
        Efficient batch matching of multiple listings against filters
        
        Args:
            listings: List of Listing objects
            filters: List of UserFilter objects to check
            
        Returns:
            Dictionary mapping listing_id -> list of matching UserFilter objects
        """
        matches = {}
        
        for listing in listings:
            matching_filters = await self.get_matches_for_listing(listing, filters)
            if matching_filters:
                matches[listing.id] = matching_filters
        
        logger.info(f"📊 Batch matching: {len(matches)} listings matched out of {len(listings)} total")
        return matches

