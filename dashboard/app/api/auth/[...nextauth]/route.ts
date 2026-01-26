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
  // Set the base URL for OAuth callbacks
  url: process.env.NEXTAUTH_URL,
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'identify email guilds',
        },
      },
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
      if (user) {
        token.id = user.id;
      }
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
  },
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/test-auth',
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };

