'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

interface Brand {
  name: string;
  count: number;
}

interface Listing {
  id: number;
  external_id: string;
  market: string;
  title: string;
  brand: string;
  price_jpy: number;
  price_usd: number;
  image_url: string | null;
  listing_url: string;
  first_seen: string;
}

interface SearchResponse {
  listings: Listing[];
  pagination: {
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

function timeAgo(dateString: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function getProxyLinks(listing: Listing): { zenMarketUrl: string; buyeeUrl: string } {
  let zenMarketUrl = '';
  let buyeeUrl = '';
  
  if (listing.market === 'yahoo') {
    // Extract Yahoo auction ID from listing URL
    // URL format: https://page.auctions.yahoo.co.jp/jp/auction/{id}
    const match = listing.listing_url.match(/auction\/([a-z][0-9]+)/i);
    const auctionId = match ? match[1] : '';
    
    if (auctionId) {
      zenMarketUrl = `https://zenmarket.jp/en/auction.aspx?itemCode=${auctionId}`;
      buyeeUrl = `https://buyee.jp/item/yahoo/auction/${auctionId}`;
    }
  } else if (listing.market === 'mercari') {
    // Extract Mercari item ID from listing URL or external_id
    // URL format: https://jp.mercari.com/item/{id}
    const match = listing.listing_url.match(/item\/([a-z0-9]+)/i);
    const itemId = match ? match[1] : listing.external_id;
    
    if (itemId) {
      zenMarketUrl = `https://zenmarket.jp/en/mercariproduct.aspx?itemCode=${itemId}`;
      buyeeUrl = `https://buyee.jp/mercari/item/${itemId}`;
    }
  }
  
  return { zenMarketUrl, buyeeUrl };
}

function ListingCard({ listing, onClick }: { listing: Listing; onClick: () => void }) {
  const [imageError, setImageError] = useState(false);

  return (
    <div 
      className="group cursor-pointer"
      onClick={onClick}
    >
      {/* Image Container */}
      <div className="relative aspect-[3/4] bg-gray-100 overflow-hidden mb-3 rounded-lg">
        <img
          src={imageError || !listing.image_url ? '/placeholder.png' : listing.image_url}
          alt={listing.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          onError={() => setImageError(true)}
        />
        {/* Market Badge */}
        <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded text-xs font-medium text-gray-700">
          {listing.market === 'yahoo' ? 'Yahoo JP' : 'Mercari'}
        </div>
      </div>

      {/* Product Info */}
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-gray-900 line-clamp-2 group-hover:underline">
          {listing.title}
        </h3>
        <p className="text-lg font-semibold text-gray-900">
          ${listing.price_usd.toFixed(0)}
        </p>
        <p className="text-xs text-gray-500">
          ¥{listing.price_jpy.toLocaleString()}
        </p>
        <p className="text-xs text-gray-400">
          {timeAgo(listing.first_seen)}
        </p>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="animate-pulse">
      <div className="aspect-[3/4] bg-gray-200 rounded-lg mb-3"></div>
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
      <div className="h-4 bg-gray-200 rounded w-1/2"></div>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
        <p className="text-gray-600">Verifying access...</p>
      </div>
    </div>
  );
}

function UpgradePrompt({ reason, userId }: { reason?: string | null; userId?: string }) {
  const getMessage = () => {
    switch (reason) {
      case 'not_in_server':
        return 'You need to join the Discord server first. Please join the server and try again.';
      case 'missing_role':
        return 'Access to the live feed requires the Instant tier subscription.';
      case 'api_error':
        return 'There was an error checking your Discord permissions. Please try again or contact support.';
      case 'error':
        return 'There was an error verifying your access. Please check that all Discord environment variables are set correctly.';
      case 'not_authenticated':
        return 'Please sign in with Discord to access the feed.';
      default:
        return 'Access to the live feed requires the Instant tier subscription.';
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h1 className="font-serif text-4xl text-gray-900 mb-4">
          {reason === 'not_in_server' ? 'Join Discord Server' : 'Upgrade Required'}
        </h1>
        <p className="text-gray-600 mb-4">
          {getMessage()}
        </p>
        {reason && (
          <p className="text-sm text-gray-400 mb-6">
            Reason: {reason}
            {userId && (
              <span className="block mt-2 text-xs">
                User ID: {userId}
              </span>
            )}
          </p>
        )}
        <div className="space-y-3">
          {reason === 'not_in_server' ? (
            <a
              href="https://discord.gg/your-server"
              className="block w-full bg-[#5865F2] text-white py-3 px-6 rounded-md hover:bg-[#4752C4] transition-colors font-medium"
            >
              Join Discord Server
            </a>
          ) : (
            <a
              href="https://whop.com/swagsearch"
              className="block w-full bg-gray-900 text-white py-3 px-6 rounded-md hover:bg-gray-800 transition-colors font-medium"
            >
              Upgrade to Instant ($30/mo)
            </a>
          )}
          <a
            href="/"
            className="block text-gray-600 hover:text-gray-900"
          >
            Back to home
          </a>
        </div>
      </div>
    </div>
  );
}

export default function FeedPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [brandSearch, setBrandSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [market, setMarket] = useState('all');
  const [sort, setSort] = useState('newest');
  const [listings, setListings] = useState<Listing[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [error, setError] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [hasAccess, setHasAccess] = useState<boolean | null>(null);
  const [accessReason, setAccessReason] = useState<string | null>(null);
  const [newItemsCount, setNewItemsCount] = useState(0);
  const [lastKnownTimestamp, setLastKnownTimestamp] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-0bd84.up.railway.app';

  // Check Discord role access
  useEffect(() => {
    async function verifyAccess() {
      if (status !== 'authenticated' || !session?.user?.id) {
        return;
      }

      try {
        const response = await fetch('/api/check-role');
        const result = await response.json();
        
        if (!response.ok) {
          // Handle error responses
          setHasAccess(false);
          setAccessReason(result.reason || 'api_error');
          console.error('Role check failed:', response.status, result);
          return;
        }
        
        setHasAccess(result.hasAccess);
        setAccessReason(result.reason || null);

        if (!result.hasAccess) {
          // Log why access denied for debugging
          console.error('❌ Access denied:', result.reason);
          console.error('User ID:', session.user.id);
          console.error('Check Vercel logs for detailed Discord API responses');
          console.error('Visit /api/debug-role to see environment variable status');
        } else {
          console.log('✅ Access granted!');
        }
      } catch (error) {
        console.error('Error verifying Discord access:', error);
        setHasAccess(false);
      }
    }

    verifyAccess();
  }, [session, status]);

  // Redirect if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/');
    }
  }, [status, router]);

  // Fetch brands on mount
  useEffect(() => {
    if (status === 'authenticated') {
      const brandsUrl = `${apiUrl}/api/brands`;
      console.log('Fetching brands from:', brandsUrl);
      fetch(brandsUrl)
        .then(res => {
          if (!res.ok) {
            throw new Error(`Failed to fetch brands: ${res.status} ${res.statusText}`);
          }
          return res.json();
        })
        .then(data => {
          console.log('Received brands:', data?.length || 0);
          setBrands(Array.isArray(data) ? data : []);
        })
        .catch(err => {
          console.error('Error fetching brands:', err);
          setError('Failed to load brands. Listings may still work.');
          setBrands([]); // Set empty array so UI doesn't break
        });
    }
  }, [status, apiUrl]);

  // Fetch listings function
  const fetchListings = useCallback(async (pageNum = 1, append = false) => {
    if (!session?.user?.id) return;

    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        discord_id: session.user.id,
        page: pageNum.toString(),
        per_page: '100',
        min_price_usd: minPrice || '0',  // Default to 0 if empty
        max_price_usd: maxPrice || '999999',  // Default to very high if empty
        market: market,
        sort: sort
      });
      
      // Add brands if any selected (OR logic - search for any of the selected brands)
      if (selectedBrands.length > 0) {
        params.append('brand', selectedBrands.join('|'));
      }

      // Add category if selected
      if (selectedCategory && selectedCategory !== 'All') {
        params.append('category', selectedCategory);
      }
      
      const url = `${apiUrl}/api/feed/search?${params}`;
      console.log('Fetching listings from:', url);
      
      const response = await fetch(url);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        console.error('API error:', response.status, response.statusText, errorText);
        throw new Error(`Failed to fetch listings: ${response.status} ${response.statusText}`);
      }

      const data: SearchResponse = await response.json();
      console.log('Received data:', {
        listingsCount: data.listings?.length || 0,
        total: data.pagination?.total || 0,
        page: data.pagination?.page || 0,
      });
      
      if (append) {
        setListings(prev => [...prev, ...data.listings]);
      } else {
        // Check if we have new items (first item has different ID)
        if (listings.length > 0 && data.listings.length > 0 && data.listings[0].id !== listings[0].id) {
          // Count how many new items
          const newCount = data.listings.findIndex(
            item => item.id === listings[0].id
          );
          if (newCount > 0) {
            setNewItemsCount(newCount);
            setTimeout(() => setNewItemsCount(0), 5000); // Clear after 5 seconds
          }
        }
        setListings(data.listings || []);
      }
      
      setTotal(data.pagination?.total || 0);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching listings:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load listings. Please try again.';
      setError(errorMessage);
      // Set empty listings on error so UI shows error state
      if (!append) {
        setListings([]);
        setTotal(0);
      }
    } finally {
      setLoading(false);
    }
  }, [session, minPrice, maxPrice, market, selectedBrands, selectedCategory, sort, apiUrl]);

  // Fetch when filters change
  useEffect(() => {
    if (status === 'authenticated' && session?.user?.id) {
      setPage(1);
      setLastKnownTimestamp(null); // Reset timestamp when filters change
      fetchListings(1, false);
    }
  }, [selectedBrands, minPrice, maxPrice, market, sort, status, session, fetchListings, selectedCategory]);

  // Smart polling - only refresh when new listings detected
  useEffect(() => {
    if (status !== 'authenticated' || !session?.user?.id || !hasAccess) return;

    async function checkForUpdates() {
      try {
        const response = await fetch(
          `${apiUrl}/api/feed/status`
        );
        const data = await response.json();
        
        // If we have a newer timestamp, refresh the feed
        if (data.latest_timestamp && data.latest_timestamp !== lastKnownTimestamp) {
          console.log('🔔 New listings detected, refreshing...');
          await fetchListings(1, false);
          setLastKnownTimestamp(data.latest_timestamp);
        }
      } catch (error) {
        console.error('Status check failed:', error);
      }
    }
    
    const interval = setInterval(checkForUpdates, 5000); // Check every 5 seconds
    return () => clearInterval(interval);
  }, [lastKnownTimestamp, selectedBrands, selectedCategory, minPrice, maxPrice, market, sort, hasAccess, fetchListings, apiUrl, status, session]);

  // Set initial timestamp when listings load
  useEffect(() => {
    if (listings.length > 0 && !lastKnownTimestamp) {
      // Get the most recent listing's timestamp
      const newest = listings[0]; // Assuming sorted by newest first
      if (newest?.first_seen) {
        setLastKnownTimestamp(newest.first_seen);
      }
    }
  }, [listings, lastKnownTimestamp]);

  const loadMore = () => {
    if (loading) return;
    const nextPage = page + 1;
    setPage(nextPage);
    fetchListings(nextPage, true);
  };


  const clearFilters = () => {
    setSelectedBrands([]);
    setSelectedCategory('All');
    setMinPrice('');
    setMaxPrice('');
    setMarket('all');
    setSort('newest');
  };

  // Show loading while checking authentication or access
  if (status === 'loading' || hasAccess === null) {
    return <LoadingScreen />;
  }

  // Redirect to login if not authenticated
  if (status === 'unauthenticated') {
    return null;
  }

  // Show upgrade prompt if no access
  if (!hasAccess) {
    return <UpgradePrompt reason={accessReason} userId={session?.user?.id} />;
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Toast Notification */}
      {newItemsCount > 0 && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg animate-slide-in">
          🔔 {newItemsCount} new {newItemsCount === 1 ? 'item' : 'items'}
        </div>
      )}
      
      {/* Top Nav */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-serif text-gray-900">SwagSearch</h1>
            {session?.user && (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>{total.toLocaleString()} items</span>
                </div>
                <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
                  {session.user.image && (
                    <Image
                      src={session.user.image}
                      alt={session.user.name || 'User'}
                      width={32}
                      height={32}
                      className="rounded-full"
                    />
                  )}
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900">
                      {session.user.name || 'User'}
                    </span>
                    <button
                      onClick={() => signOut({ callbackUrl: '/' })}
                      className="text-xs text-gray-500 hover:text-gray-700 text-left"
                    >
                      Sign out
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Filters Section */}
      <div className="border-b border-gray-200 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="space-y-4">
            {/* Brand Filter */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
                Designers
              </label>

              {/* Selected brands as removable tags */}
              {selectedBrands.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {selectedBrands.map(brand => (
                    <span
                      key={brand}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-900 text-white rounded-full text-sm"
                    >
                      {brand}
                      <button
                        onClick={() => setSelectedBrands(prev => prev.filter(b => b !== brand))}
                        className="hover:bg-gray-700 rounded-full p-0.5 transition-colors"
                        aria-label={`Remove ${brand}`}
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* Search input */}
              <div className="relative mb-2">
                <input
                  type="text"
                  placeholder="Search designers..."
                  value={brandSearch}
                  onChange={(e) => setBrandSearch(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-md text-base focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
                />
                {brandSearch && (
                  <button
                    onClick={() => setBrandSearch('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Brand checkboxes in scrollable container */}
              <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md bg-white">
                {brands
                  .filter(b => b.name.toLowerCase().includes(brandSearch.toLowerCase()))
                  .map(brand => (
                    <label
                      key={brand.name}
                      className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-100 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={selectedBrands.includes(brand.name)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedBrands(prev => [...prev, brand.name]);
                            } else {
                              setSelectedBrands(prev => prev.filter(b => b !== brand.name));
                            }
                          }}
                          className="w-4 h-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                        />
                        <span className="text-sm font-medium text-gray-900">
                          {brand.name}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {brand.count.toLocaleString()}
                      </span>
                    </label>
                  ))}
                
                {/* No results message */}
                {brands.filter(b => b.name.toLowerCase().includes(brandSearch.toLowerCase())).length === 0 && (
                  <div className="px-4 py-8 text-center text-gray-500 text-sm">
                    No designers found matching "{brandSearch}"
                  </div>
                )}
              </div>
            </div>

            {/* Category Filter */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
                Category
              </label>
              <div className="flex flex-wrap gap-2">
                {['All', 'Jackets', 'Tops', 'Pants', 'Shoes', 'Bags', 'Accessories'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`
                      px-4 py-2 text-sm font-medium rounded-md transition-all
                      ${selectedCategory === cat
                        ? 'bg-gray-900 text-white'
                        : 'bg-white border border-gray-300 text-gray-700 hover:border-gray-900'
                      }
                    `}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Price Range */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
                Price Range
              </label>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">
                    Min Price
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                    <input
                      type="number"
                      placeholder="0"
                      value={minPrice}
                      onChange={(e) => setMinPrice(e.target.value)}
                      className="w-full pl-7 pr-3 py-3 text-base border border-gray-300 rounded-md focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">
                    Max Price
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                    <input
                      type="number"
                      placeholder="0"
                      value={maxPrice}
                      onChange={(e) => setMaxPrice(e.target.value)}
                      className="w-full pl-7 pr-3 py-3 text-base border border-gray-300 rounded-md focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Source and Sort */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
                  Source
                </label>
                <select
                  value={market}
                  onChange={(e) => setMarket(e.target.value)}
                  className="w-full px-3 py-3 border border-gray-300 rounded-md text-base focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
                >
                  <option value="all">All Sources</option>
                  <option value="yahoo">Yahoo Japan</option>
                  <option value="mercari">Mercari</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
                  Sort By
                </label>
                <select 
                  value={sort}
                  onChange={(e) => setSort(e.target.value)}
                  className="w-full px-3 py-3 border border-gray-300 rounded-md text-base focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
                >
                  <option value="newest">Newest</option>
                  <option value="price_low">Price: Low to High</option>
                  <option value="price_high">Price: High to Low</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Results Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error State */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600 text-sm">{error}</p>
            <button
              onClick={() => fetchListings(1, false)}
              className="mt-2 text-red-600 hover:text-red-700 underline text-sm"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty State */}
        {listings.length === 0 && !loading && (
          <div className="text-center py-20">
            <div className="max-w-md mx-auto">
              <p className="text-2xl font-serif text-gray-900 mb-2">
                No items found
              </p>
              <p className="text-gray-600 mb-6">
                Try adjusting your filters or browse all designers
              </p>
              <button
                onClick={clearFilters}
                className="px-6 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition-colors font-medium"
              >
                Clear All Filters
              </button>
            </div>
          </div>
        )}

        {/* Loading Skeleton */}
        {loading && listings.length === 0 && (
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(12)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Listings Grid */}
        {listings.length > 0 && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
              {listings.map((listing) => (
                <ListingCard 
                  key={listing.id} 
                  listing={listing}
                  onClick={() => setSelectedListing(listing)}
                />
              ))}
            </div>

            {/* Load More Button */}
            <div className="flex justify-center mt-12">
              <button
                onClick={loadMore}
                disabled={loading}
                className="px-8 py-3 border-2 border-gray-900 text-gray-900 rounded-md hover:bg-gray-900 hover:text-white transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Loading...' : `Load More (${total - listings.length} remaining)`}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Detail Modal */}
      {selectedListing && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 overflow-y-auto"
          onClick={() => setSelectedListing(null)}
        >
          <div className="min-h-screen flex items-center justify-center p-4">
            <div 
              className="bg-white rounded-lg max-w-5xl w-full shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="grid md:grid-cols-2">
                {/* Left: Image */}
                <div className="bg-gray-100 p-8">
                  <button
                    onClick={() => setSelectedListing(null)}
                    className="mb-4 text-gray-600 hover:text-gray-900 text-sm font-medium"
                  >
                    ← Back
                  </button>
                  <img
                    src={selectedListing.image_url || '/placeholder.png'}
                    alt={selectedListing.title}
                    className="w-full rounded-lg"
                  />
                </div>

                {/* Right: Details */}
                <div className="p-8 space-y-6">
                  <div>
                    <h2 className="font-serif text-3xl text-gray-900 mb-2">
                      {selectedListing.title}
                    </h2>
                    {selectedListing.brand && (
                      <p className="text-sm text-gray-500 uppercase tracking-wide">
                        {selectedListing.brand}
                      </p>
                    )}
                  </div>

                  <div>
                    <p className="text-4xl font-bold text-gray-900">
                      ${selectedListing.price_usd.toFixed(0)}
                    </p>
                    <p className="text-gray-500 mt-1">
                      ¥{selectedListing.price_jpy.toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="px-3 py-1 bg-gray-100 rounded-full">
                      {selectedListing.market === 'yahoo' ? 'Yahoo Japan Auction' : 'Mercari'}
                    </span>
                    <span>•</span>
                    <span>Listed {timeAgo(selectedListing.first_seen)}</span>
                  </div>

                  <div className="space-y-3 pt-4">
                    {/* Get proxy links */}
                    {(() => {
                      const { zenMarketUrl, buyeeUrl } = getProxyLinks(selectedListing);
                      return (
                        <>
                          <a
                            href={selectedListing.listing_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block w-full bg-gray-900 text-white text-center py-3 px-6 rounded-md hover:bg-gray-800 transition-colors font-medium"
                          >
                            View Original Listing
                          </a>
                          
                          {/* Proxy Service Buttons (Side by Side) */}
                          <div className="grid grid-cols-2 gap-3">
                            {zenMarketUrl && (
                              <a
                                href={zenMarketUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block w-full border-2 border-gray-900 text-gray-900 text-center py-3 px-4 rounded-md hover:bg-gray-50 transition-colors font-medium"
                              >
                                ZenMarket
                              </a>
                            )}
                            
                            {buyeeUrl && (
                              <a
                                href={buyeeUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block w-full border-2 border-gray-900 text-gray-900 text-center py-3 px-4 rounded-md hover:bg-gray-50 transition-colors font-medium"
                              >
                                Buyee
                              </a>
                            )}
                          </div>
                          
                          <a
                            href={`https://lens.google.com/uploadbyurl?url=${encodeURIComponent(selectedListing.image_url || '')}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block w-full border border-gray-300 text-gray-700 text-center py-3 px-6 rounded-md hover:border-gray-900 transition-colors"
                          >
                            🔍 Reverse Image Search
                          </a>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
