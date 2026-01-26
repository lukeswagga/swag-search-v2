import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { getToken } from 'next-auth/jwt';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';
import { checkDiscordRole } from '@/lib/discord';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  try {
    // Get the session from the server
    const session = await getServerSession(authOptions);

    if (!session || !session.user?.id) {
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated' },
        { status: 401 }
      );
    }

    console.log('Session check:', {
      hasSession: !!session,
      userId: session.user.id,
      userName: session.user.name,
      sessionAccessToken: !!(session as any).accessToken,
    });

    // Try to get access token from session first (most reliable)
    let accessToken: string | null = null;
    
    // First, try session accessToken (set in session callback)
    if ((session as any).accessToken && typeof (session as any).accessToken === 'string') {
      accessToken = (session as any).accessToken;
      console.log('✅ Using access token from session');
    }
    // Fallback to JWT token
    else {
      // Get cookies for token retrieval
      const cookieStore = await cookies();
      const allCookies = cookieStore.getAll();
      const cookieHeader = allCookies.map(c => `${c.name}=${c.value}`).join('; ');
      
      // Get the access token from JWT
      const token = await getToken({ 
        req: {
          headers: {
            cookie: cookieHeader,
          },
          url: request.url,
        } as any,
        secret: process.env.NEXTAUTH_SECRET 
      });

      console.log('Token check:', {
        hasToken: !!token,
        hasAccessToken: !!token?.accessToken,
        tokenKeys: token ? Object.keys(token) : [],
      });

      if (token?.accessToken && typeof token.accessToken === 'string') {
        accessToken = token.accessToken;
        console.log('✅ Using access token from JWT');
      }
    }
    
    if (!accessToken) {
      console.error('❌ Missing access token in both session and JWT', {
        sessionHasAccessToken: !!(session as any).accessToken,
      });
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated', details: 'Access token not found. The OAuth flow may not have completed properly. Please sign out and sign in again.' },
        { status: 401 }
      );
    }

    // Optional admin bypass - only if ADMIN_DISCORD_IDS is set
    const ADMIN_DISCORD_IDS = process.env.ADMIN_DISCORD_IDS?.split(',').map(id => id.trim()).filter(id => id.length > 0) || [];
    if (ADMIN_DISCORD_IDS.length > 0 && ADMIN_DISCORD_IDS.includes(session.user.id)) {
      console.log('Admin access granted via bypass');
      return NextResponse.json({
        hasAccess: true,
        reason: 'authorized' as const,
      });
    }

    // Check Discord role
    console.log('Starting Discord role check for user:', session.user.id);
    const result = await checkDiscordRole(
      accessToken,
      session.user.id,
      'Instant'
    );
    
    console.log('Role check result:', JSON.stringify(result, null, 2));

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error checking Discord role:', error);
    return NextResponse.json(
      { hasAccess: false, reason: 'error' },
      { status: 500 }
    );
  }
}

