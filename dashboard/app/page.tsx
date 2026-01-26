'use client';

import Link from 'next/link';
import { signIn, signOut, useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Home() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const handleBrowseFeed = () => {
    console.log('Browse feed clicked, status:', status, 'session:', session?.user?.id);
    if (status === 'authenticated') {
      router.push('/feed');
    } else {
      signIn('discord', { callbackUrl: '/feed' });
    }
  };
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative h-screen flex items-center">
        {/* Background with subtle gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-gray-50 to-white"></div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
          <div className="max-w-3xl">
            <h1 className="font-serif text-6xl lg:text-7xl text-gray-900 mb-6">
              Designer Fashion
              <br />
              from Japan, Live
            </h1>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Browse 14,000+ curated pieces from Yahoo Japan and Mercari. 
              Updated every 5 minutes with new finds from Rick Owens, Raf Simons, 
              Comme des Garçons, and more.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={handleBrowseFeed}
                className="px-8 py-4 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition-colors font-medium text-lg text-center"
              >
                {status === 'loading' 
                  ? 'Loading...' 
                  : status === 'authenticated' 
                    ? 'Browse Live Feed' 
                    : 'Sign in with Discord'}
              </button>
              <a
                href="#how-it-works"
                className="px-8 py-4 border-2 border-gray-900 text-gray-900 rounded-md hover:bg-gray-50 transition-colors font-medium text-lg text-center"
              >
                How It Works
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="how-it-works" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="font-serif text-4xl text-center text-gray-900 mb-16">
            Why SwagSearch?
          </h2>
          
          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-3xl">🔍</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Live Updates
              </h3>
              <p className="text-gray-600">
                New listings appear every 5 minutes. Never miss a deal on your grails.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-3xl">🇯🇵</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Japan Exclusive
              </h3>
              <p className="text-gray-600">
                Access Yahoo Japan auctions and Mercari - where the archive pieces live.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-3xl">⚡</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Filter & Find
              </h3>
              <p className="text-gray-600">
                Search by brand, set price ranges, and let the algorithm do the hunting.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Screenshot Section */}
      <section className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="font-serif text-4xl text-gray-900 mb-6">
                Browse Like a Pro
              </h2>
              <p className="text-xl text-gray-600 mb-6">
                Select your favorite designers, set your budget, and scroll through 
                live results. Every piece is authenticated by the marketplace and ready 
                to ship via proxy services like ZenMarket.
              </p>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <span className="text-green-600 font-bold">✓</span>
                  <span className="text-gray-700">14,000+ active listings</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-600 font-bold">✓</span>
                  <span className="text-gray-700">Updated every 5 minutes</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-600 font-bold">✓</span>
                  <span className="text-gray-700">Direct links to buy with proxy</span>
                </li>
              </ul>
            </div>
            
            <div className="bg-white rounded-lg shadow-2xl p-4">
              {/* Screenshot placeholder - add actual screenshot */}
              <div className="aspect-[4/3] bg-gray-200 rounded flex items-center justify-center">
                <span className="text-gray-400">Feed Screenshot</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-serif text-4xl text-gray-900 mb-6">
            One Simple Plan
          </h2>
          <p className="text-xl text-gray-600 mb-12">
            Full access to live feed, unlimited searches, and priority support
          </p>
          
          <div className="bg-gray-50 rounded-2xl p-12 max-w-md mx-auto">
            <h3 className="text-2xl font-bold text-gray-900 mb-2">
              Instant Tier
            </h3>
            <div className="text-5xl font-bold text-gray-900 mb-6">
              $30<span className="text-2xl text-gray-600">/mo</span>
            </div>
            <ul className="text-left space-y-3 mb-8">
              <li className="flex items-start gap-3">
                <span className="text-green-600 font-bold">✓</span>
                <span>Unlimited live feed access</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-600 font-bold">✓</span>
                <span>Real-time updates every 5 min</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-600 font-bold">✓</span>
                <span>Discord community access</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-600 font-bold">✓</span>
                <span>Priority customer support</span>
              </li>
            </ul>
            
            <a
              href="https://whop.com/swagsearch"
              className="block w-full bg-gray-900 text-white py-4 rounded-md hover:bg-gray-800 transition-colors font-medium text-lg"
            >
              Start Browsing
            </a>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gray-900 text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-serif text-4xl mb-6">
            Ready to find your grails?
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Join resellers and collectors already using SwagSearch
          </p>
          
          <button
            onClick={handleBrowseFeed}
            className="inline-block px-8 py-4 bg-white text-gray-900 rounded-md hover:bg-gray-100 transition-colors font-medium text-lg"
          >
            {status === 'loading' 
              ? 'Loading...' 
              : status === 'authenticated' 
                ? 'Browse Live Feed →' 
                : 'Sign in with Discord →'}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <p className="font-serif text-xl text-gray-900">SwagSearch</p>
              <p className="text-sm text-gray-600 mt-1">Designer fashion from Japan, live</p>
            </div>
            <div className="flex gap-6 text-sm text-gray-600">
              <a href="https://discord.gg/your-server" className="hover:text-gray-900">Discord</a>
              <a href="https://instagram.com/your-handle" className="hover:text-gray-900">Instagram</a>
              <a href="mailto:support@swagsearch.com" className="hover:text-gray-900">Support</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
