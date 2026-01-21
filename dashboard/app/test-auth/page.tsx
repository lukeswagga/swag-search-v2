'use client';

import { signIn, signOut, useSession } from 'next-auth/react';
import Image from 'next/image';

export default function TestAuthPage() {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
        <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg dark:bg-zinc-900">
          <h1 className="mb-6 text-2xl font-bold text-black dark:text-zinc-50">
            Authentication Test
          </h1>
          
          <div className="mb-6 space-y-4">
            <div className="flex items-center gap-4">
              {session.user?.image && (
                <Image
                  src={session.user.image}
                  alt="Avatar"
                  width={64}
                  height={64}
                  className="rounded-full"
                />
              )}
              <div>
                <p className="text-lg font-semibold text-black dark:text-zinc-50">
                  {session.user?.name || 'Unknown User'}
                </p>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  {session.user?.email}
                </p>
              </div>
            </div>
            
            <div className="rounded-md bg-zinc-100 p-4 dark:bg-zinc-800">
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Discord ID:
              </p>
              <p className="mt-1 font-mono text-sm text-zinc-900 dark:text-zinc-100">
                {(session.user as any)?.discord_id || session.user?.id}
              </p>
            </div>
            
            <div className="rounded-md bg-zinc-100 p-4 dark:bg-zinc-800">
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                User ID:
              </p>
              <p className="mt-1 font-mono text-sm text-zinc-900 dark:text-zinc-100">
                {session.user?.id}
              </p>
            </div>
          </div>
          
          <button
            onClick={() => signOut()}
            className="w-full rounded-md bg-red-600 px-4 py-2 text-white transition-colors hover:bg-red-700"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg dark:bg-zinc-900">
        <h1 className="mb-6 text-2xl font-bold text-black dark:text-zinc-50">
          Authentication Test
        </h1>
        
        <p className="mb-6 text-zinc-600 dark:text-zinc-400">
          Sign in with Discord to test authentication
        </p>
        
        <button
          onClick={() => signIn('discord')}
          className="w-full rounded-md bg-[#5865F2] px-4 py-2 text-white transition-colors hover:bg-[#4752C4]"
        >
          Sign in with Discord
        </button>
      </div>
    </div>
  );
}

