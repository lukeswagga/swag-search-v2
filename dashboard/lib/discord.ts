export interface DiscordRoleCheckResult {
  hasAccess: boolean;
  reason: 'authorized' | 'not_in_server' | 'missing_role' | 'api_error' | 'error';
}

export async function checkDiscordRole(
  accessToken: string,
  userId: string,
  requiredRole: string = 'Instant'
): Promise<DiscordRoleCheckResult> {
  try {
    const YOUR_SERVER_ID = process.env.DISCORD_GUILD_ID;
    const DISCORD_BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;
    const INSTANT_ROLE_ID = process.env.DISCORD_INSTANT_ROLE_ID;

    if (!YOUR_SERVER_ID || !DISCORD_BOT_TOKEN || !INSTANT_ROLE_ID) {
      const missing = [];
      if (!YOUR_SERVER_ID) missing.push('DISCORD_GUILD_ID');
      if (!DISCORD_BOT_TOKEN) missing.push('DISCORD_BOT_TOKEN');
      if (!INSTANT_ROLE_ID) missing.push('DISCORD_INSTANT_ROLE_ID');
      console.error('Missing Discord environment variables:', missing.join(', '));
      return { hasAccess: false, reason: 'error' };
    }

    // Get user's guilds (servers) using their access token
    const guildsResponse = await fetch('https://discord.com/api/users/@me/guilds', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!guildsResponse.ok) {
      const errorText = await guildsResponse.text().catch(() => 'Unknown error');
      console.error('Failed to fetch user guilds:', guildsResponse.status, errorText);
      return { hasAccess: false, reason: 'api_error' };
    }

    const guilds = await guildsResponse.json();

    // Check if user is in your server
    const inServer = guilds.some((guild: any) => guild.id === YOUR_SERVER_ID);

    if (!inServer) {
      return { hasAccess: false, reason: 'not_in_server' };
    }

    // Get user's roles in your server using bot token
    const memberResponse = await fetch(
      `https://discord.com/api/guilds/${YOUR_SERVER_ID}/members/${userId}`,
      {
        headers: {
          Authorization: `Bot ${DISCORD_BOT_TOKEN}`,
        },
      }
    );

    if (!memberResponse.ok) {
      if (memberResponse.status === 404) {
        // User is not in the server (edge case)
        return { hasAccess: false, reason: 'not_in_server' };
      }
      console.error('Failed to fetch guild member:', memberResponse.status);
      return { hasAccess: false, reason: 'api_error' };
    }

    const member = await memberResponse.json();
    const roles = member.roles || [];

    // Check if user has required role
    const hasRole = roles.includes(INSTANT_ROLE_ID);
    
    console.log('Role check:', {
      userId,
      roles,
      requiredRoleId: INSTANT_ROLE_ID,
      hasRole,
    });

    return {
      hasAccess: hasRole,
      reason: hasRole ? 'authorized' : 'missing_role',
    };
  } catch (error) {
    console.error('Discord role check failed:', error);
    return { hasAccess: false, reason: 'error' };
  }
}

