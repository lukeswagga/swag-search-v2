import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { getToken } from 'next-auth/jwt';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';
import { checkDiscordRole } from '@/lib/discord';

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

    // Get the access token from JWT
    // Convert NextRequest to format getToken expects
    const token = await getToken({ 
      req: {
        headers: Object.fromEntries(request.headers.entries()),
      } as any,
      secret: process.env.NEXTAUTH_SECRET 
    });

    if (!token || !token.accessToken || typeof token.accessToken !== 'string') {
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated' },
        { status: 401 }
      );
    }

    // Admin bypass - check if user is admin
    const ADMIN_DISCORD_IDS = process.env.ADMIN_DISCORD_IDS?.split(',').map(id => id.trim()) || [];
    if (ADMIN_DISCORD_IDS.includes(session.user.id)) {
      return NextResponse.json({
        hasAccess: true,
        reason: 'authorized' as const,
      });
    }

    // Check Discord role
    const result = await checkDiscordRole(
      token.accessToken,
      session.user.id,
      'Instant'
    );

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error checking Discord role:', error);
    return NextResponse.json(
      { hasAccess: false, reason: 'error' },
      { status: 500 }
    );
  }
}

