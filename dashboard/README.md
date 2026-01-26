This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Environment Variables

Required environment variables for Discord OAuth and role verification:

```bash
# Discord OAuth (already configured)
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret

# Discord Role Verification (NEW - required for feed access)
DISCORD_GUILD_ID=your_discord_server_id
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_INSTANT_ROLE_ID=your_instant_role_id

# NextAuth
NEXTAUTH_SECRET=your_nextauth_secret
NEXTAUTH_URL=https://swag-search-v2.vercel.app  # Production URL (use http://localhost:3000 for local dev)

# API
NEXT_PUBLIC_API_URL=https://web-production-0bd84.up.railway.app
```

### Getting Discord Role ID

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on the "Instant" role in your Discord server
3. Click "Copy ID" - this is your `DISCORD_INSTANT_ROLE_ID`

### Discord Bot Setup

Your Discord bot needs:
- `GUILD_MEMBERS` intent enabled in Discord Developer Portal
- Bot must be in your server with appropriate permissions
- Bot token from Discord Developer Portal

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

**Important:** Make sure to add all environment variables in Vercel's project settings before deploying.
