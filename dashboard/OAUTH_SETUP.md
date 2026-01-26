# Discord OAuth Setup Guide

## Fix "Invalid OAuth2 redirect_uri" Error

### Step 1: Your Production URL
Your production URL is: **`https://swag-search-v2.vercel.app`**

### Step 2: Add Redirect URI in Discord Developer Portal

1. Go to https://discord.com/developers/applications
2. Select your Discord application
3. Go to **OAuth2** → **General**
4. Under **Redirects**, click **Add Redirect**
5. Add this EXACT URL (copy it exactly, no trailing slash):

```
https://swag-search-v2.vercel.app/api/auth/callback/discord
```

6. If you also want to test locally, add:
```
http://localhost:3000/api/auth/callback/discord
```

7. Click **Save Changes**

### Step 3: Verify NEXTAUTH_URL in Vercel

1. Go to your Vercel project dashboard
2. Go to **Settings** → **Environment Variables**
3. Make sure `NEXTAUTH_URL` is set to:
```
https://swag-search-v2.vercel.app
```

**Important:** 
- No trailing slash
- Use `https://` (not `http://`)
- Must match your production domain exactly

### Step 4: Redeploy

After adding the redirect URI in Discord and verifying NEXTAUTH_URL:
1. Go to Vercel → Deployments
2. Click the three dots on the latest deployment
3. Click **Redeploy**

### Common Issues

**Issue:** Still getting "Invalid OAuth2 redirect_uri"
- **Fix:** Make sure the URL in Discord matches EXACTLY (case-sensitive, no trailing slash)
- **Fix:** Wait a few minutes after saving in Discord (sometimes takes time to propagate)
- **Fix:** Clear browser cache and try again

**Issue:** Works locally but not in production
- **Fix:** Make sure you added BOTH redirect URIs (localhost and production)
- **Fix:** Verify NEXTAUTH_URL is set correctly in Vercel

**Issue:** Redirect works but shows "Upgrade Required"
- **Fix:** Check that user has the "Instant" role in your Discord server
- **Fix:** Verify DISCORD_INSTANT_ROLE_ID matches the actual role ID
- **Fix:** Make sure user is in the Discord server

## Testing

1. Clear browser cookies
2. Go to `https://swag-search-v2.vercel.app`
3. Click "Sign in with Discord"
4. Should redirect to Discord OAuth
5. After authorizing, should redirect back to `/feed`
6. If you have the Instant role, you should see the feed
7. If not, you'll see the upgrade prompt with the reason

