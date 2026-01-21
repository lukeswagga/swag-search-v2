import NextAuth, { NextAuthOptions, Profile } from 'next-auth';
import DiscordProvider from 'next-auth/providers/discord';
import { query } from '@/lib/db';

// Extend Profile type for Discord
interface DiscordProfile extends Profile {
  id: string;
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
          scope: 'identify email',
        },
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account, profile }: { user: any; account: any; profile?: DiscordProfile }) {
      if (account?.provider === 'discord' && user) {
        try {
          const discordId = user.id || profile?.id || account.providerAccountId;
          const discordUsername = user.name || profile?.username;
          const discordAvatar = user.image || profile?.avatar || profile?.image_url;
          const email = user.email || profile?.email;

          if (!discordId) {
            console.error('No Discord ID found');
            return false;
          }

          // Check if user exists
          const existingUser = await query(
            'SELECT * FROM users WHERE discord_id = $1',
            [discordId]
          );

          if (existingUser.rows.length === 0) {
            // Insert new user
            await query(
              `INSERT INTO users (discord_id, discord_username, discord_avatar, email, created_at, updated_at)
               VALUES ($1, $2, $3, $4, NOW(), NOW())`,
              [discordId, discordUsername, discordAvatar, email]
            );
            console.log(`New user created: ${discordId}`);
          } else {
            // Update existing user info
            await query(
              `UPDATE users 
               SET discord_username = $2, discord_avatar = $3, email = $4, updated_at = NOW()
               WHERE discord_id = $1`,
              [discordId, discordUsername, discordAvatar, email]
            );
            console.log(`User updated: ${discordId}`);
          }

          return true;
        } catch (error) {
          console.error('Error in signIn callback:', error);
          return false;
        }
      }
      return true;
    },
    async session({ session, token }) {
      if (session.user) {
        try {
          // Get user from database
          const result = await query(
            'SELECT discord_id, discord_username, discord_avatar FROM users WHERE discord_id = $1',
            [token.sub]
          );

          if (result.rows.length > 0) {
            const dbUser = result.rows[0];
            session.user = {
              ...session.user,
              id: token.sub as string,
              discord_id: dbUser.discord_id,
              name: dbUser.discord_username || session.user.name,
              image: dbUser.discord_avatar || session.user.image,
            };
          } else {
            // Fallback to token data if not in DB
            session.user = {
              ...session.user,
              id: token.sub as string,
              discord_id: token.sub as string,
            };
          }
        } catch (error) {
          console.error('Error in session callback:', error);
          // Fallback to token data on error
          session.user = {
            ...session.user,
            id: token.sub as string,
            discord_id: token.sub as string,
          };
        }
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

