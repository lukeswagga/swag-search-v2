'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { Slider } from '@/components/ui/slider';

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

function getZenMarketLink(listing: Listing): string {
  if (listing.market === 'yahoo') {
    const match = listing.listing_url.match(/\/([a-z0-9]+)$/);
    return `https://zenmarket.jp/en/yahoo.aspx?itemCode=${match ? match[1] : ''}`;
  }
  return listing.listing_url;
}

function ListingCard({ listing }: { listing: Listing }) {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden hover:ring-2 hover:ring-indigo-500 transition">
      <img 
        src={imageError || !listing.image_url ? '/placeholder.png' : listing.image_url}
        alt={listing.title}
        className="w-full h-64 object-cover"
        onError={() => setImageError(true)}
      />
      <div className="p-4">
        <h3 className="text-white font-medium mb-2 line-clamp-2">
          {listing.title}
        </h3>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-2xl font-bold text-green-400">
            ${listing.price_usd.toFixed(0)}
          </span>
          <span className="text-gray-400">
            ¥{listing.price_jpy.toLocaleString()}
          </span>
        </div>
        <div className="text-sm text-gray-400 mb-3">
          {listing.market === 'yahoo' ? 'Yahoo JP' : 'Mercari'} • {timeAgo(listing.first_seen)}
        </div>
        <div className="flex gap-2">
          <a 
            href={listing.listing_url} 
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-2 text-center rounded transition-colors"
          >
            View
          </a>
          <a 
            href={getZenMarketLink(listing)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 text-center rounded transition-colors"
          >
            ZenMarket
          </a>
          <a 
            href={`https://lens.google.com/uploadbyurl?url=${encodeURIComponent(listing.image_url || '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gray-700 hover:bg-gray-600 text-white py-2 px-3 rounded transition-colors"
            title="Google Lens"
          >
            🔍
          </a>
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden animate-pulse">
      <div className="w-full h-64 bg-gray-700" />
      <div className="p-4">
        <div className="h-4 bg-gray-700 rounded mb-2" />
        <div className="h-6 bg-gray-700 rounded w-24 mb-2" />
        <div className="h-3 bg-gray-700 rounded w-32 mb-3" />
        <div className="flex gap-2">
          <div className="flex-1 h-8 bg-gray-700 rounded" />
          <div className="flex-1 h-8 bg-gray-700 rounded" />
          <div className="w-8 h-8 bg-gray-700 rounded" />
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
  const [priceRange, setPriceRange] = useState([0, 1000]);
  const [market, setMarket] = useState('all');
  const [listings, setListings] = useState<Listing[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-0bd84.up.railway.app';

  // Redirect if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/');
    }
  }, [status, router]);

  // Fetch brands on mount
  useEffect(() => {
    if (status === 'authenticated') {
      fetch(`${apiUrl}/api/brands`)
        .then(res => res.json())
        .then(data => setBrands(data))
        .catch(err => {
          console.error('Error fetching brands:', err);
          setError('Failed to load brands');
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
        min_price_usd: priceRange[0].toString(),
        max_price_usd: priceRange[1].toString(),
        market: market,
        sort: 'newest'
      });
      
      // Add brands if any selected (OR logic - search for any of the selected brands)
      if (selectedBrands.length > 0) {
        params.append('brand', selectedBrands.join('|'));
      }
      
      const response = await fetch(
        `${apiUrl}/api/feed/search?${params}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch listings');
      }

      const data: SearchResponse = await response.json();
      
      if (append) {
        setListings(prev => [...prev, ...data.listings]);
      } else {
        setListings(data.listings);
      }
      
      setTotal(data.pagination.total);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching listings:', err);
      setError('Failed to load listings. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [session, priceRange, market, selectedBrands, apiUrl]);

  // Fetch when filters change
  useEffect(() => {
    if (status === 'authenticated' && session?.user?.id) {
      setPage(1);
      fetchListings(1, false);
    }
  }, [selectedBrands, priceRange, market, status, session, fetchListings]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (status !== 'authenticated' || !session?.user?.id) return;

    const interval = setInterval(() => {
      fetchListings(1, false);
    }, 30000);
    
    return () => clearInterval(interval);
  }, [status, session, fetchListings]);

  const loadMore = () => {
    if (loading) return;
    const nextPage = page + 1;
    setPage(nextPage);
    fetchListings(nextPage, true);
  };

  const toggleBrand = (brandName: string) => {
    setSelectedBrands(prev => 
      prev.includes(brandName)
        ? prev.filter(b => b !== brandName)
        : [...prev, brandName]
    );
  };

  const clearFilters = () => {
    setSelectedBrands([]);
    setPriceRange([0, 1000]);
    setMarket('all');
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(6)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Live Indicator Banner */}
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-between sticky top-0 z-10 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span className="text-white font-medium">LIVE</span>
          <span className="text-gray-400">• {total.toLocaleString()} items</span>
        </div>
        <span className="text-gray-400 text-sm">
          Updated {timeAgo(lastUpdate.toISOString())}
        </span>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Brand Selector */}
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-400 mb-3">Brands</h2>
          <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
            {brands.map(brand => (
              <button
                key={brand.name}
                onClick={() => toggleBrand(brand.name)}
                className={`
                  px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors
                  ${selectedBrands.includes(brand.name)
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }
                `}
              >
                {brand.name} ({brand.count})
              </button>
            ))}
          </div>
        </div>

        {/* Price Range Slider */}
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-400 mb-3">Price Range</h2>
          <div className="px-2">
            <Slider
              min={0}
              max={1000}
              step={10}
              value={priceRange}
              onValueChange={(value) => setPriceRange(value as [number, number])}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-gray-400 mt-2">
              <span>${priceRange[0]}</span>
              <span>${priceRange[1]}</span>
            </div>
          </div>
        </div>

        {/* Market Selector */}
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-400 mb-3">Market</h2>
          <div className="flex gap-4">
            {['all', 'yahoo', 'mercari'].map(m => (
              <label key={m} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="market"
                  checked={market === m}
                  onChange={() => setMarket(m)}
                  className="w-4 h-4 text-indigo-600 bg-gray-800 border-gray-600 focus:ring-indigo-500"
                />
                <span className="text-gray-300">
                  {m === 'all' ? 'All' : m === 'yahoo' ? 'Yahoo JP' : 'Mercari'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 bg-red-900/20 border border-red-500 rounded-lg p-4">
            <p className="text-red-400">{error}</p>
            <button
              onClick={() => fetchListings(1, false)}
              className="mt-2 text-red-400 hover:text-red-300 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Results Header */}
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-white">
            Showing {listings.length} {listings.length === 1 ? 'result' : 'results'}
          </h2>
        </div>

        {/* Empty State */}
        {listings.length === 0 && !loading && (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg mb-4">
              No listings found with current filters
            </p>
            <button 
              onClick={clearFilters}
              className="text-indigo-400 hover:text-indigo-300 underline"
            >
              Clear filters
            </button>
          </div>
        )}

        {/* Listings Grid */}
        {listings.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {listings.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>

            {/* Load More Button */}
            {loading ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="text-gray-400 mt-2">Loading...</p>
              </div>
            ) : (
              <div className="text-center py-8">
                <button
                  onClick={loadMore}
                  disabled={loading}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-8 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Load More 100 Items
                </button>
              </div>
            )}
          </>
        )}

        {/* Loading Skeleton */}
        {loading && listings.length === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(6)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
