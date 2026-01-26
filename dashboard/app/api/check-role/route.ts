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

    // Get cookies for token retrieval - try both cookie names
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get('next-auth.session-token') || 
                         cookieStore.get('__Secure-next-auth.session-token') ||
                         cookieStore.get('authjs.session-token') ||
                         cookieStore.get('__Secure-authjs.session-token');
    
    if (!sessionCookie) {
      console.error('No session cookie found');
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated', details: 'No session cookie' },
        { status: 401 }
      );
    }
    
    // Build cookie header
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
      userId: token?.sub || token?.id,
      sessionUserId: session.user.id,
    });

    if (!token) {
      console.error('No token found');
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated', details: 'JWT token not found' },
        { status: 401 }
      );
    }

    if (!token.accessToken || typeof token.accessToken !== 'string') {
      console.error('Missing access token in JWT', {
        tokenKeys: Object.keys(token),
        hasSub: !!token.sub,
        hasId: !!token.id,
      });
      // Try to get access token from session if available
      const sessionAccessToken = (session as any).accessToken;
      if (sessionAccessToken && typeof sessionAccessToken === 'string') {
        console.log('Using access token from session');
        // Use session access token as fallback
        const result = await checkDiscordRole(
          sessionAccessToken,
          session.user.id,
          'Instant'
        );
        return NextResponse.json(result);
      }
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated', details: 'Access token not found in session. Please sign out and sign in again.' },
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
      token.accessToken,
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

