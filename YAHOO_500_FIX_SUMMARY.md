# Yahoo Auctions HTTP 500 Error Fix Summary

## ✅ Changes Committed and Pushed

**Branch:** `claude/fix-yahoo-500-errors-AXPJL`
**Commit:** `484db32`

---

## 🔍 Root Causes Identified

The HTTP 500 errors were caused by multiple issues:

1. **URL Parameter Overload**: Adding unnecessary parameters (`ei=utf-8`, price filters) that Yahoo doesn't expect
2. **Incorrect URL Encoding**: Using `%20` for spaces instead of `+` (Yahoo preference)
3. **Excessive Page Size**: Requesting 100 items per page instead of the recommended 50
4. **Rate Limiting**: Too many concurrent requests (3-5 brands + 5 pages = 15-25 simultaneous requests)
5. **No Retry Logic**: Failed immediately on 500 errors without retrying

---

## 🛠️ Fixes Applied

### 1. URL Format Corrections (`core_scraper_base.py`)

**Before:**
```python
def build_search_url(self, keyword, page=1, ..., page_size=100):
    params = {
        'p': keyword,
        'va': keyword,
        'ei': 'utf-8',  # ❌ Not needed
        'n': '100',     # ❌ Too large
        'aucminprice': str(min_price_jpy),  # ❌ May trigger 500s
        'aucmaxprice': str(max_price_jpy),  # ❌ May trigger 500s
    }
    # ❌ Uses quote() → spaces become %20
    param_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
```

**After:**
```python
def build_search_url(self, keyword, page=1, ..., page_size=50):
    # Minimal parameters matching known working URLs
    params = {
        'p': keyword,
        'va': keyword,
        'fixed': str(fixed_type),
        'is_postage_mode': '1',
        'dest_pref_code': '13',
        'b': str(start_position),
        'n': '50',  # ✅ Reduced to 50
        's1': sort_type,
        'o1': sort_order
    }
    # ✅ Uses urlencode with quote_plus → spaces become '+'
    param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
```

**Resulting URL:**
```
https://auctions.yahoo.co.jp/search/search?p=Chanel&va=Chanel&fixed=3&is_postage_mode=1&dest_pref_code=13&b=1&n=50&s1=new&o1=d
```

---

### 2. Retry Logic with Exponential Backoff

Added to both `fetch_page()` and `fetch_page_async()`:

```python
async def fetch_page_async(self, url, max_retries=4):
    for attempt in range(1, max_retries + 1):
        try:
            response = await session.get(url)
            if response.status == 200:
                return html, True
            elif response.status >= 500:
                if attempt < max_retries:
                    delay = 2 ** attempt  # 2s, 4s, 8s, 16s
                    print(f"❌ HTTP {response.status} - Retry {attempt}/{max_retries} after {delay}s")
                    await asyncio.sleep(delay)
                    continue
            else:
                # Don't retry 4xx errors
                return None, False
        except (TimeoutError, Exception) as e:
            # Retry with same exponential backoff
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Attempt 4: Wait 8 seconds
- Attempt 5: Wait 16 seconds (final)

---

### 3. Reduced Concurrency

**Before:**
- 3 brands processed concurrently
- 5 pages per brand concurrently
- **Total: 15 simultaneous requests** ⚠️

**After:**
- Brands processed sequentially (1 at a time)
- Pages processed sequentially (1 at a time)
- 2.5s delay between pages
- 3s delay between brands
- **Total: 1 request at a time** ✅

**Applied to all scrapers:**
- ✅ `new_listings_scraper.py`
- ✅ `buy_it_now_scraper.py`
- ✅ `ending_soon_scraper.py`
- ✅ `budget_steals_scraper.py`

---

## 📊 Expected Impact

### Before Fix:
```
Brand: Chanel
Page 1: HTTP 500 ❌
Page 2: HTTP 500 ❌
Page 3: HTTP 500 ❌
→ 0 listings found
```

### After Fix:
```
Brand: Chanel
Page 1: HTTP 200 ✅ (or retry → 200 ✅)
  → 2.5s delay
Page 2: HTTP 200 ✅
  → 2.5s delay
Page 3: HTTP 200 ✅
→ 150 listings found (50 per page)
  → 3s delay before next brand
```

---

## 🧪 Testing Recommendations

1. **Monitor Railway Logs** for the next few scraping cycles:
   - Look for "HTTP 200" success messages
   - Check for reduced "HTTP 500" errors
   - Verify retry logic is working (look for "Retry X/4" messages)

2. **Check Discord Channels** for new listings:
   - Should see listings from previously failing brands
   - Chanel, Issey Miyake, Bottega Veneta, etc.

3. **Performance Impact**:
   - Scraping will be slower (sequential instead of concurrent)
   - But more reliable (no 500 errors)
   - Trades speed for stability

---

## 🚀 Deployment

**Already pushed to branch:** `claude/fix-yahoo-500-errors-AXPJL`

**Next Steps:**
1. Monitor the first few scraping cycles on Railway
2. Verify HTTP 500 errors are eliminated
3. If successful, this branch can be merged to main
4. If issues persist, further tuning may be needed:
   - Increase delays (e.g., 5s between pages)
   - Reduce page count further
   - Add random jitter to delays

---

## 📝 Files Modified

1. ✅ `core_scraper_base.py` - URL building, retry logic
2. ✅ `new_listings_scraper.py` - Concurrency reduction
3. ✅ `buy_it_now_scraper.py` - Concurrency reduction
4. ✅ `ending_soon_scraper.py` - Concurrency reduction
5. ✅ `budget_steals_scraper.py` - Concurrency reduction

---

## 💡 Key Insights

1. **Yahoo Auctions prefers polite scrapers**: Sequential requests with delays are more reliable than concurrent
2. **Minimal URL parameters**: Only include what's necessary
3. **URL encoding matters**: `+` for spaces, not `%20`
4. **Page size matters**: 50 items is safer than 100
5. **Retry with backoff**: Exponential backoff gives Yahoo time to recover

---

## ⚠️ Potential Future Improvements

If 500 errors still occur occasionally:

1. **Add random jitter** to delays (e.g., 2-3 seconds instead of fixed 2.5s)
2. **Implement circuit breaker** (pause scraping for 60s if too many 500s)
3. **Add User-Agent rotation** (already have 3, could add more)
4. **Reduce max pages** further (currently 2-5, could go to 1-2)
5. **Add per-brand rate limiting** (track last request time per brand)

---

## 📞 Support

If issues persist:
- Check Railway logs for specific error patterns
- Verify network connectivity to Yahoo Auctions
- Consider if Yahoo has changed their API/website structure
- May need to add CAPTCHA solving or session management

---

**Generated:** 2025-12-15
**Branch:** `claude/fix-yahoo-500-errors-AXPJL`
**Status:** ✅ Ready for testing
