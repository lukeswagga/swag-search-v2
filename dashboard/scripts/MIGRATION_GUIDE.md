# How to Run the Database Migration

There are several ways to run the SQL migration to create the `users` table. Choose the method that works best for you.

## Method 1: Using the Migration Script (Easiest) ⭐

This is the recommended method. Make sure you have your `.env.local` file set up with `DATABASE_URL`.

```bash
npm run migrate
```

This will:
- Read the SQL file
- Connect to your PostgreSQL database
- Execute all the SQL statements
- Verify the table was created

## Method 2: Using Railway's Web Interface

1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Look for "Query" or "Data" tab
4. Copy and paste the contents of `scripts/create-users-table.sql`
5. Click "Run" or "Execute"

## Method 3: Using psql Command Line

If you have `psql` installed locally:

```bash
# Get your DATABASE_URL from Railway
# Format: postgresql://user:password@host:port/database

psql $DATABASE_URL -f scripts/create-users-table.sql
```

Or if you prefer to paste it directly:

```bash
psql $DATABASE_URL
```

Then paste the SQL content and press Enter.

## Method 4: Using a Database Client

Use a GUI tool like:
- **pgAdmin** (https://www.pgadmin.org/)
- **DBeaver** (https://dbeaver.io/)
- **TablePlus** (https://tableplus.com/)
- **Postico** (Mac only)

1. Connect to your Railway PostgreSQL database using your `DATABASE_URL`
2. Open a SQL query window
3. Copy and paste the contents of `scripts/create-users-table.sql`
4. Execute the query

## Method 5: Using Railway CLI

If you have Railway CLI installed:

```bash
railway connect postgres
railway run psql < scripts/create-users-table.sql
```

## Verify the Migration

After running the migration, you can verify it worked by checking if the table exists:

```sql
SELECT * FROM users;
```

Or check the table structure:

```sql
\d users
```

## Troubleshooting

**Error: "relation users already exists"**
- This is fine! The migration uses `CREATE TABLE IF NOT EXISTS`, so it's safe to run multiple times.

**Error: "connection refused" or "could not connect"**
- Check your `DATABASE_URL` in `.env.local`
- Make sure your Railway database is running
- Verify the connection string format is correct

**Error: "permission denied"**
- Make sure your database user has CREATE TABLE permissions
- Check that you're connecting to the correct database

