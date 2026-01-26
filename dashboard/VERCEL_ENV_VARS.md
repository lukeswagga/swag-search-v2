# Vercel Environment Variables Checklist

## Required Environment Variables in Vercel

Add these in **Vercel → Settings → Environment Variables**:

### Discord OAuth
```
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
```

### Discord Role Verification
```
DISCORD_GUILD_ID=your_discord_server_id
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_INSTANT_ROLE_ID=your_instant_role_id
```

### NextAuth
```
NEXTAUTH_SECRET=your_nextauth_secret
NEXTAUTH_URL=https://swag-search-v2.vercel.app
```

### Optional Admin Bypass
```
ADMIN_DISCORD_IDS=your_discord_user_id,another_admin_id
```
(Only set this if you want to bypass role checks for specific users)

### API
```
NEXT_PUBLIC_API_URL=https://web-production-0bd84.up.railway.app
```

## ❌ DO NOT ADD THESE AS ENVIRONMENT VARIABLES

These are **NOT** environment variables - they go in **Discord Developer Portal**:

- `https://swag-search-v2.vercel.app/api/auth/callback/discord` → Add in Discord OAuth2 Redirects
- `http://localhost:3000/api/auth/callback/discord` → Add in Discord OAuth2 Redirects (for local dev)

## Important Notes

1. **NEXTAUTH_URL** should be just the base URL: `https://swag-search-v2.vercel.app`
   - ❌ NOT: `https://swag-search-v2.vercel.app/api/auth/callback/discord`
   - ✅ YES: `https://swag-search-v2.vercel.app`

2. **Redirect URIs** are configured in Discord Developer Portal, not Vercel
   - Go to: https://discord.com/developers/applications
   - Your App → OAuth2 → General → Redirects
   - Add: `https://swag-search-v2.vercel.app/api/auth/callback/discord`

3. After adding/updating environment variables:
   - Redeploy your Vercel project
   - Changes take effect on the next deployment

