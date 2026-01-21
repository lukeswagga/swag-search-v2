import { config } from 'dotenv';

// Load environment variables
config({ path: '.env.local' });

console.log('🔍 Checking OAuth Configuration...\n');

// Check NEXTAUTH_URL
const nextAuthUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
console.log(`NEXTAUTH_URL: ${nextAuthUrl}`);

// Construct the redirect URI that NextAuth will use
const redirectUri = `${nextAuthUrl}/api/auth/callback/discord`;
console.log(`\n✅ Redirect URI (what Discord expects):`);
console.log(`   ${redirectUri}\n`);

// Check Discord credentials
console.log('Discord OAuth Credentials:');
console.log(`   DISCORD_CLIENT_ID: ${process.env.DISCORD_CLIENT_ID ? '✅ Set' : '❌ Not set'}`);
console.log(`   DISCORD_CLIENT_SECRET: ${process.env.DISCORD_CLIENT_SECRET ? '✅ Set' : '❌ Not set'}`);
console.log(`   NEXTAUTH_SECRET: ${process.env.NEXTAUTH_SECRET ? '✅ Set' : '❌ Not set'}\n`);

console.log('📋 Steps to fix "Invalid OAuth2 redirect_uri" error:\n');
console.log('1. Go to https://discord.com/developers/applications');
console.log('2. Select your application');
console.log('3. Go to "OAuth2" → "General"');
console.log('4. Under "Redirects", click "Add Redirect"');
console.log(`5. Add this EXACT URL (copy it exactly):`);
console.log(`\n   ${redirectUri}\n`);
console.log('6. Important:');
console.log('   - Use http://localhost:3000 (NOT 127.0.0.1)');
console.log('   - No trailing slash');
console.log('   - Exact path: /api/auth/callback/discord');
console.log('   - Case sensitive');
console.log('\n7. Click "Save Changes"');
console.log('8. Try signing in again\n');

