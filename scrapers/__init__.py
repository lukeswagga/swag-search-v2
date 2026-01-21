"""
Scrapers package for v2
"""
import sys
import os

# Add parent directory to path for absolute imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from .yahoo_scraper import YahooScraper
    from .mercari_api_scraper import MercariAPIScraper
    from .base import BaseScraper
except ImportError:
    from scrapers.yahoo_scraper import YahooScraper
    from scrapers.mercari_api_scraper import MercariAPIScraper
    from scrapers.base import BaseScraper

__all__ = ['YahooScraper', 'MercariAPIScraper', 'BaseScraper']

