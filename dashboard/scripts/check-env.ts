import { config } from 'dotenv';
import { existsSync } from 'fs';
import { join } from 'path';

console.log('🔍 Checking environment configuration...\n');

// Check if .env.local exists
const envPath = join(process.cwd(), '.env.local');
if (!existsSync(envPath)) {
  console.error('❌ .env.local file not found!');
  console.error(`   Expected location: ${envPath}\n`);
  console.error('Please create .env.local in the dashboard/ directory with:');
  console.error('DATABASE_URL=postgresql://user:password@host:port/database');
  process.exit(1);
}

console.log('✅ .env.local file found');

// Load environment variables
config({ path: '.env.local' });

// Check DATABASE_URL
if (!process.env.DATABASE_URL) {
  console.error('\n❌ DATABASE_URL is not set in .env.local');
  process.exit(1);
}

const dbUrl = process.env.DATABASE_URL;
const maskedUrl = dbUrl.replace(/:[^:@]+@/, ':****@');
console.log(`✅ DATABASE_URL is set: ${maskedUrl}`);

// Check if it looks like a Railway URL
if (dbUrl.includes('railway.app') || dbUrl.includes('railway')) {
  console.log('✅ Looks like a Railway database URL');
} else if (dbUrl.includes('localhost') || dbUrl.includes('127.0.0.1')) {
  console.warn('⚠️  Warning: DATABASE_URL points to localhost');
  console.warn('   Make sure you\'re using your Railway PostgreSQL URL, not localhost');
}

// Check other required vars
console.log('\n📋 Other environment variables:');
console.log(`   DISCORD_CLIENT_ID: ${process.env.DISCORD_CLIENT_ID ? '✅ Set' : '❌ Not set'}`);
console.log(`   DISCORD_CLIENT_SECRET: ${process.env.DISCORD_CLIENT_SECRET ? '✅ Set' : '❌ Not set'}`);
console.log(`   NEXTAUTH_URL: ${process.env.NEXTAUTH_URL || '❌ Not set'}`);
console.log(`   NEXTAUTH_SECRET: ${process.env.NEXTAUTH_SECRET ? '✅ Set' : '❌ Not set'}`);

console.log('\n✅ Environment check complete!');

