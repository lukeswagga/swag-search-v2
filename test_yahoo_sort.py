#!/usr/bin/env python3
"""
Test script to verify Yahoo sort parameters and compare URLs
This helps debug which sort parameter actually gives newest listings first
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.yahoo_scraper import YahooScraper

def test_sort_parameters():
    """Test different sort parameters and show URLs"""
    
    scraper = YahooScraper()
    keyword = "Rick Owens"
    
    print("=" * 80)
    print("🧪 Testing Yahoo Sort Parameters")
    print("=" * 80)
    print(f"Keyword: {keyword}\n")
    
    # Test different sort options
    sort_options = [
        ("new", "d", "Newest first (s1=new, o1=d)"),
        ("new", "a", "Oldest first (s1=new, o1=a)"),
        ("cbids", "d", "Current bids desc (s1=cbids, o1=d) - CURRENTLY USED"),
        ("cbids", "a", "Current bids asc (s1=cbids, o1=a)"),
        ("end", "a", "Ending soonest (s1=end, o1=a)"),
        ("end", "d", "Ending latest (s1=end, o1=d)"),
    ]
    
    print("📋 Generated URLs with different sort parameters:\n")
    for sort_type, sort_order, description in sort_options:
        url = scraper.build_search_url(
            keyword=keyword,
            page=1,
            sort_type=sort_type,
            sort_order=sort_order
        )
        print(f"{description}:")
        print(f"  {url}\n")
    
    print("=" * 80)
    print("🔍 INSTRUCTIONS:")
    print("=" * 80)
    print("1. Open Chrome and go to Yahoo Japan Auctions")
    print("2. Search for 'Rick Owens'")
    print("3. Click the sort dropdown and select '新着順' (Newest)")
    print("4. Copy the URL from your browser's address bar")
    print("5. Compare it with the URLs above to see which parameters Yahoo uses")
    print("\n💡 Look for the 's1' and 'o1' parameters in the URL")
    print("   Example: ...&s1=new&o1=d...")
    print("=" * 80)

if __name__ == "__main__":
    test_sort_parameters()

