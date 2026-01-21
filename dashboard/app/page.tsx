import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-white mb-4">
          SwagSearch
        </h1>
        <p className="text-xl text-gray-300 mb-8">
          Real-time fashion arbitrage alerts from Yahoo Japan + Mercari
        </p>
        <Link
          href="/api/auth/signin"
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-lg text-lg"
        >
          Sign In with Discord
        </Link>
      </div>
    </div>
  );
}
