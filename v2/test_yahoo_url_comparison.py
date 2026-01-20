#!/usr/bin/env python3
"""
Compare scraper-generated URLs with Chrome URL to verify they match
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.yahoo_scraper import YahooScraper

def compare_urls():
    """Compare scraper URL with Chrome URL"""
    
    scraper = YahooScraper()
    keyword = "rick owens"
    
    # Generate URL with newest sort (should match Chrome now)
    url = scraper.build_search_url(
        keyword=keyword,
        page=1,
        fixed_type=3,  # This will be ignored for newest sort
        sort_type="new",
        sort_order="d"
    )
    
    # Chrome URL from user
    chrome_url = "https://auctions.yahoo.co.jp/search/search?p=rick+owens&va=rick+owens&is_postage_mode=1&dest_pref_code=13&b=1&n=50&s1=new&o1=d"
    
    print("=" * 80)
    print("🔍 URL Comparison")
    print("=" * 80)
    print(f"\n📱 Chrome URL (from browser):")
    print(f"   {chrome_url}")
    print(f"\n🤖 Scraper URL (generated):")
    print(f"   {url}")
    
    # Extract parameters from both URLs
    def extract_params(url_str):
        """Extract query parameters from URL"""
        if '?' not in url_str:
            return {}
        query = url_str.split('?')[1]
        params = {}
        for pair in query.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
        return params
    
    chrome_params = extract_params(chrome_url)
    scraper_params = extract_params(url)
    
    print(f"\n📊 Parameter Comparison:")
    print(f"\n   Chrome has: {sorted(chrome_params.keys())}")
    print(f"   Scraper has: {sorted(scraper_params.keys())}")
    
    # Check differences
    chrome_only = set(chrome_params.keys()) - set(scraper_params.keys())
    scraper_only = set(scraper_params.keys()) - set(chrome_params.keys())
    common = set(chrome_params.keys()) & set(scraper_params.keys())
    
    if chrome_only:
        print(f"\n   ⚠️  Chrome has but scraper doesn't: {chrome_only}")
    if scraper_only:
        print(f"\n   ⚠️  Scraper has but Chrome doesn't: {scraper_only}")
    
    # Check if values match for common parameters
    print(f"\n   ✅ Common parameters:")
    mismatches = []
    for key in sorted(common):
        chrome_val = chrome_params[key]
        scraper_val = scraper_params[key]
        match = "✅" if chrome_val == scraper_val else "❌"
        print(f"      {match} {key}: Chrome='{chrome_val}' vs Scraper='{scraper_val}'")
        if chrome_val != scraper_val:
            mismatches.append((key, chrome_val, scraper_val))
    
    if not chrome_only and not scraper_only and not mismatches:
        print(f"\n   🎉 URLs MATCH! (ignoring domain and encoding differences)")
    else:
        print(f"\n   ⚠️  URLs differ - may need adjustment")
    
    print("=" * 80)

if __name__ == "__main__":
    compare_urls()

