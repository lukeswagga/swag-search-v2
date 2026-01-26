import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';
import { checkDiscordRole } from '@/lib/discord';

export async function GET(request: NextRequest) {
  try {
    // Get the session from the server
    const session = await getServerSession(authOptions);

    if (!session || !session.accessToken || !session.user?.id) {
      return NextResponse.json(
        { hasAccess: false, reason: 'not_authenticated' },
        { status: 401 }
      );
    }

    // Check Discord role
    const result = await checkDiscordRole(
      session.accessToken,
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

