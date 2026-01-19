"""
Simple test to check if Yahoo Japan is blocking your IP
Tests a single request with minimal code
"""
import requests
import time

def test_yahoo_connection():
    """Test if we can reach Yahoo Auctions"""
    
    # Simple test URL
    test_url = "https://auctions.yahoo.co.jp/search/search?p=Supreme&va=Supreme&fixed=3&is_postage_mode=1&dest_pref_code=13&b=1&n=50&s1=new&o1=d"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en;q=0.5',
    }
    
    print("=" * 60)
    print("Testing Yahoo Japan Auctions Connection")
    print("=" * 60)
    print(f"URL: {test_url[:80]}...")
    print()
    
    try:
        print("Making request...")
        response = requests.get(test_url, headers=headers, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS - IP is NOT blocked")
            print(f"   Response length: {len(response.text)} bytes")
            if 'Product' in response.text:
                count = response.text.count('class="Product')
                print(f"   Found ~{count} product listings")
            return True
        elif response.status_code == 500:
            print("❌ HTTP 500 - IP is likely BLOCKED")
            print("   Yahoo Japan has temporarily blocked your IP address")
            print("   Solutions:")
            print("   1. Wait 30-60 minutes before trying again")
            print("   2. Use a different network (mobile hotspot, VPN)")
            print("   3. Check if you can access yahoo.co.jp in a browser")
            return False
        elif response.status_code == 429:
            print("⚠️  HTTP 429 - Rate limited (not blocked)")
            print("   Wait a few minutes and try again")
            return False
        else:
            print(f"❌ HTTP {response.status_code} - Unexpected error")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT - Request took too long")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR - {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR - {e}")
        return False
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    result = test_yahoo_connection()
    
    print()
    if not result:
        print("💡 RECOMMENDATIONS:")
        print("   1. Wait 30-60 minutes before running the scraper again")
        print("   2. Try accessing https://auctions.yahoo.co.jp in your browser")
        print("   3. If browser works but script doesn't, it's an IP block")
        print("   4. Consider using a VPN or different network for testing")
    else:
        print("✅ Your IP is working! You can run the scraper now.")

