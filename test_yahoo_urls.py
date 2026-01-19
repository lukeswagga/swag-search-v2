#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify Yahoo Auctions URL formats
"""
import requests
import urllib.parse
import time

def test_url(url, description):
    """Test a single URL and report status"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            print(f"✅ SUCCESS - HTTP {response.status_code}")
            # Count items found
            if 'Product' in response.text:
                count = response.text.count('class="Product')
                print(f"   Found approximately {count} product listings")
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"❌ ERROR - {e}")
        return None

def build_url_old_method(keyword):
    """Build URL using old method (quote with %20)"""
    base_url = "https://auctions.yahoo.co.jp/search/search"
    params = {
        'p': keyword,
        'va': keyword,
        'fixed': '3',
        'is_postage_mode': '1',
        'dest_pref_code': '13',
        'b': '1',
        'n': '100',
        's1': 'new',
        'o1': 'd',
        'ei': 'utf-8',
        'aucminprice': '441',
        'aucmaxprice': '220500'
    }
    param_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
    return f"{base_url}?{param_string}"

def build_url_quote_plus(keyword):
    """Build URL using quote_plus (spaces as +)"""
    base_url = "https://auctions.yahoo.co.jp/search/search"
    params = {
        'p': keyword,
        'va': keyword,
        'fixed': '3',
        'is_postage_mode': '1',
        'dest_pref_code': '13',
        'b': '1',
        'n': '50',
        's1': 'new',
        'o1': 'd'
    }
    param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
    return f"{base_url}?{param_string}"

def build_url_minimal(keyword):
    """Build URL with minimal parameters (like working example)"""
    base_url = "https://auctions.yahoo.co.jp/search/search"
    params = {
        'p': keyword,
        'va': keyword,
        'fixed': '3',
        'is_postage_mode': '1',
        'dest_pref_code': '13',
        'b': '1',
        'n': '50',
        's1': 'new',
        'o1': 'd'
    }
    # Manually construct to ensure + for spaces
    param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
    return f"{base_url}?{param_string}"

def build_url_no_va(keyword):
    """Build URL without va parameter"""
    base_url = "https://auctions.yahoo.co.jp/search/search"
    params = {
        'p': keyword,
        'fixed': '3',
        'is_postage_mode': '1',
        'dest_pref_code': '13',
        'b': '1',
        'n': '50',
        's1': 'new',
        'o1': 'd'
    }
    param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
    return f"{base_url}?{param_string}"

def main():
    print("🧪 Yahoo Auctions URL Format Testing")
    print("=" * 60)

    # Test brands that are known to cause 500 errors
    test_brands = [
        ("Chanel", "Chanel"),
        ("Issey Miyake", "Issey Miyake"),
        ("Bottega Veneta", "Bottega Veneta"),
        ("Rick Owens", "Rick Owens"),
        ("dolce gabanna", "dolce gabanna (lowercase, no &)")
    ]

    for brand_name, description in test_brands:
        print(f"\n\n{'#'*60}")
        print(f"# Testing Brand: {description}")
        print(f"{'#'*60}")

        # Test 1: Old method with %20 and extra params
        url1 = build_url_old_method(brand_name)
        test_url(url1, f"OLD METHOD (n=100, with price filters, ei=utf-8)")
        time.sleep(2)

        # Test 2: Quote plus with minimal params
        url2 = build_url_minimal(brand_name)
        test_url(url2, f"MINIMAL (n=50, no price filters, quote_plus)")
        time.sleep(2)

        # Test 3: No va parameter
        url3 = build_url_no_va(brand_name)
        test_url(url3, f"NO VA PARAM (n=50, no va)")
        time.sleep(2)

        # Add delay between brands
        time.sleep(3)

    print("\n\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
