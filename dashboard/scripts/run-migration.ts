import { readFileSync } from 'fs';
import { join } from 'path';
import { config } from 'dotenv';

// Load environment variables FIRST (synchronously)
config({ path: '.env.local' });

async function runMigration() {
  try {
    // Check if DATABASE_URL is set
    if (!process.env.DATABASE_URL) {
      console.error('❌ Error: DATABASE_URL is not set in .env.local');
      console.error('\nPlease add your Railway PostgreSQL connection string:');
      console.error('DATABASE_URL=postgresql://user:password@host:port/database\n');
      console.error('You can find this in your Railway project:');
      console.error('1. Go to your Railway project dashboard');
      console.error('2. Click on your PostgreSQL service');
      console.error('3. Go to the "Variables" tab');
      console.error('4. Copy the DATABASE_URL or PGDATABASE value\n');
      console.error('Make sure .env.local is in the dashboard/ directory');
      process.exit(1);
    }

    // Show connection info (without password)
    const dbUrl = process.env.DATABASE_URL;
    const maskedUrl = dbUrl.replace(/:[^:@]+@/, ':****@');
    console.log(`🔌 Connecting to: ${maskedUrl}`);
    
    // Import db after env is loaded
    const { query, closePool } = await import('../lib/db');
    
    console.log('📖 Reading migration file...');
    const sqlPath = join(process.cwd(), 'scripts', 'create-users-table.sql');
    const sql = readFileSync(sqlPath, 'utf-8');
    
    // Remove comments and split by semicolons
    const cleanedSql = sql
      .split('\n')
      .map(line => {
        // Remove inline comments
        const commentIndex = line.indexOf('--');
        if (commentIndex >= 0) {
          return line.substring(0, commentIndex);
        }
        return line;
      })
      .join('\n');
    
    // Split by semicolons and filter empty statements
    const statements = cleanedSql
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.match(/^\s*$/));

    console.log(`📝 Found ${statements.length} SQL statement(s) to execute\n`);

    for (let i = 0; i < statements.length; i++) {
      const statement = statements[i];
      const preview = statement.split('\n')[0].substring(0, 60);
      console.log(`[${i + 1}/${statements.length}] Executing: ${preview}...`);
      await query(statement);
    }

    console.log('\n✅ Migration completed successfully!');
    
    // Verify the table was created
    console.log('🔍 Verifying table creation...');
    const result = await query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name = 'users'
    `);
    
    if (result.rows.length > 0) {
      console.log('✅ Verified: users table exists');
      
      // Show table structure
      const columns = await query(`
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'users'
        ORDER BY ordinal_position
      `);
      
      console.log('\n📊 Table structure:');
      columns.rows.forEach(col => {
        console.log(`   - ${col.column_name} (${col.data_type})`);
      });
    } else {
      console.log('⚠️  Warning: users table not found after migration');
    }
    
    await closePool();
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Migration failed:');
    if (error instanceof Error) {
      console.error(error.message);
      
      // Provide helpful error messages
      if (error.message.includes('ECONNREFUSED') || (error as any).code === 'ECONNREFUSED') {
        console.error('\n💡 Troubleshooting:');
        console.error('1. Check that your DATABASE_URL in .env.local is correct');
        console.error('2. Make sure your Railway PostgreSQL service is running');
        console.error('3. Verify the connection string format:');
        console.error('   DATABASE_URL=postgresql://user:password@host:port/database');
        console.error('4. For Railway, the URL should look like:');
        console.error('   postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway');
        console.error('\n5. Check your .env.local file location - it should be in the dashboard/ directory');
        console.error('6. Make sure there are no extra spaces or quotes around the DATABASE_URL value');
      }
    } else {
      console.error(error);
    }
    try {
      const { closePool } = await import('../lib/db');
      await closePool();
    } catch {}
    process.exit(1);
  }
}

runMigration();
