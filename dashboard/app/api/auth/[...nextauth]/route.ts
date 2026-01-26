import NextAuth, { NextAuthOptions, Profile } from 'next-auth';
import DiscordProvider from 'next-auth/providers/discord';

// Extend Profile type for Discord
interface DiscordProfile extends Profile {
  id?: string;
  username?: string;
  avatar?: string;
  discriminator?: string;
  image_url?: string;
}

export const authOptions: NextAuthOptions = {
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'identify email guilds',
        },
      },
      // Ensure proper callback handling
      checks: ['state'],
    }),
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      if (account?.provider === 'discord' && user) {
        // Type assertion for Discord profile
        const discordProfile = profile as DiscordProfile | undefined;
        const discordId = user.id || discordProfile?.id || account.providerAccountId;

        if (!discordId) {
          console.error('No Discord ID found');
          return false;
        }

        // Log successful sign-in
        console.log('Discord sign-in successful', {
          userId: discordId,
          hasAccessToken: !!account.access_token,
        });

        // TODO: Call Railway API to save user if needed
        // User data will be saved via API calls from other parts of the dashboard
        // Example: await fetch('https://web-production-0bd84.up.railway.app/api/users', { ... })

        return true;
      }
      return true;
    },
    async session({ session, token }) {
      if (session.user) {
        // Use token data directly - no database connection needed
        // User data will be fetched from Railway API when needed
        session.user = {
          ...session.user,
          id: token.sub as string,
          discord_id: token.sub as string,
        };
        // Expose access token for Discord API calls
        session.accessToken = token.accessToken as string;
      }
      return session;
    },
    async jwt({ token, user, account, profile }) {
      // Initial sign in - store user ID and access token
      if (account && user) {
        token.id = user.id;
        token.accessToken = account.access_token;
        console.log('JWT callback: Initial sign in', { 
          userId: user.id,
          hasAccessToken: !!account.access_token,
          provider: account.provider,
          tokenLength: account.access_token?.length
        });
      }
      // Subsequent requests - preserve existing access token and user ID
      // IMPORTANT: Always preserve the existing accessToken
      if (user) {
        token.id = user.id;
      }
      // If accessToken exists, keep it (don't overwrite with undefined)
      if (!token.accessToken && account?.access_token) {
        token.accessToken = account.access_token;
        console.log('JWT callback: Restored access token from account');
      }
      return token;
    },
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60, // 24 hours
  },
  cookies: {
    sessionToken: {
      name: `next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
        maxAge: 30 * 24 * 60 * 60, // 30 days
      },
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };

