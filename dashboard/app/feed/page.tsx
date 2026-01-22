'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Loader2 } from 'lucide-react';

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

function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function getBuyeeLink(listingUrl: string, market: string): string {
  if (market === 'yahoo') {
    // Extract Yahoo auction ID from URL
    const match = listingUrl.match(/\/([a-z0-9]+)$/);
    const auctionId = match ? match[1] : '';
    return `https://buyee.jp/item/yahoo/auction/${auctionId}`;
  }
  // For Mercari, just return the listing URL (Buyee supports Mercari too)
  return listingUrl;
}

function ListingCard({ listing }: { listing: Listing }) {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden hover:ring-2 hover:ring-indigo-500 transition">
      <img 
        src={imageError || !listing.image_url ? '/placeholder.png' : listing.image_url} 
        alt={listing.title}
        className="w-full h-48 object-cover"
        onError={() => setImageError(true)}
      />
      <div className="p-4">
        <h3 className="text-white font-medium truncate mb-2">
          {listing.title}
        </h3>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-2xl font-bold text-green-400">
            ¥{listing.price_jpy.toLocaleString()}
          </span>
          <span className="text-gray-400">
            ${listing.price_usd.toFixed(0)}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
          <span className={listing.market === 'yahoo' ? 'text-purple-400' : 'text-blue-400'}>
            {listing.market === 'yahoo' ? 'Yahoo JP' : 'Mercari'}
          </span>
          <span>•</span>
          <span>{timeAgo(listing.first_seen)}</span>
        </div>
        <div className="flex gap-2">
          <a 
            href={listing.listing_url} 
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-2 px-3 rounded text-sm text-center transition-colors"
          >
            View
          </a>
          <a 
            href={getBuyeeLink(listing.listing_url, listing.market)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 px-3 rounded text-sm text-center transition-colors"
          >
            Buyee
          </a>
          <a 
            href={`https://lens.google.com/uploadbyurl?url=${encodeURIComponent(listing.image_url || '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gray-700 hover:bg-gray-600 text-white py-2 px-3 rounded text-sm transition-colors"
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
      <div className="w-full h-48 bg-gray-700" />
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
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-0bd84.up.railway.app';

  // Redirect if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/');
    }
  }, [status, router]);

  // Fetch feed on mount
  useEffect(() => {
    if (status === 'authenticated' && session?.user?.id) {
      fetchFeed();
    }
  }, [status, session]);

  const fetchFeed = async () => {
    if (!session?.user?.id) return;

    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(
        `${apiUrl}/api/feed?discord_id=${session.user.id}&limit=50`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch feed');
      }

      const data = await response.json();
      setListings(data || []);
    } catch (error) {
      console.error('Error fetching feed:', error);
      setError('Failed to load feed. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">Your Personal Feed</h1>
            <p className="text-gray-400">Loading your feed...</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Your Personal Feed</h1>
          <p className="text-gray-400">
            {listings.length > 0 
              ? `Showing ${listings.length} item${listings.length !== 1 ? 's' : ''}`
              : 'No listings yet'}
          </p>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 bg-red-900/20 border border-red-500 rounded-lg p-4">
            <p className="text-red-400">{error}</p>
            <button
              onClick={fetchFeed}
              className="mt-2 text-red-400 hover:text-red-300 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!error && listings.length === 0 && (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
            <p className="text-gray-400 text-lg mb-6">
              No listings yet! Your filters will start finding matches soon.
            </p>
            <Link
              href="/filters"
              className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-lg text-lg transition-colors"
            >
              Create a Filter
            </Link>
          </div>
        )}

        {/* Listings Grid */}
        {!error && listings.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {listings.map((listing) => (
              <ListingCard key={listing.id} listing={listing} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

