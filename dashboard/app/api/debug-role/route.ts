import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { getToken } from 'next-auth/jwt';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session || !session.user?.id) {
      return NextResponse.json({
        authenticated: false,
        message: 'Not authenticated'
      });
    }

    const token = await getToken({ 
      req: {
        headers: Object.fromEntries(request.headers.entries()),
      } as any,
      secret: process.env.NEXTAUTH_SECRET 
    });

    // Check environment variables
    const envCheck = {
      DISCORD_GUILD_ID: process.env.DISCORD_GUILD_ID ? '✅ Set' : '❌ Missing',
      DISCORD_BOT_TOKEN: process.env.DISCORD_BOT_TOKEN ? '✅ Set' : '❌ Missing',
      DISCORD_INSTANT_ROLE_ID: process.env.DISCORD_INSTANT_ROLE_ID ? '✅ Set' : '❌ Missing',
      ADMIN_DISCORD_IDS: process.env.ADMIN_DISCORD_IDS || 'Not set (optional)',
      hasAccessToken: token?.accessToken ? '✅ Yes' : '❌ No',
    };

    return NextResponse.json({
      authenticated: true,
      userId: session.user.id,
      userName: session.user.name,
      environmentVariables: envCheck,
      accessTokenPresent: !!token?.accessToken,
      message: 'Check Vercel logs for detailed role check results'
    });
  } catch (error) {
    return NextResponse.json({
      error: 'Failed to get debug info',
      message: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

