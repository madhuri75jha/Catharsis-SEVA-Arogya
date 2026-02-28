# Automatic Database Migrations

## Overview

Database migrations run automatically when the application starts. This ensures your database schema is always up-to-date without manual intervention.

## How It Works

1. **On Application Startup**: The `MigrationManager` checks for pending migrations
2. **Migration Tracking**: Applied migrations are tracked in the `schema_migrations` table
3. **Sequential Execution**: Migrations are applied in alphabetical order (001, 002, 003, etc.)
4. **Idempotent**: Safe to run multiple times - already applied migrations are skipped

## Migration File Naming Convention

Migrations must follow this naming pattern:
```
NNN_description.sql
```

Examples:
- `001_add_streaming_columns.sql` ✅
- `002_add_user_preferences.sql` ✅
- `rollback_script.sql` ❌ (will be ignored)
- `001_add_streaming_columns_rollback.sql` ❌ (will be ignored)

## Creating New Migrations

1. **Create SQL file** in `migrations/` directory:
```bash
touch migrations/002_your_migration_name.sql
```

2. **Write migration SQL**:
```sql
-- Migration: Add new feature
-- Date: 2024-01-15

ALTER TABLE your_table
ADD COLUMN new_column VARCHAR(255);

CREATE INDEX idx_new_column ON your_table(new_column);
```

3. **Deploy**: The migration runs automatically on next deployment

## Checking Migration Status

### Via Health Endpoint
```bash
curl https://your-app-url.com/health
```

Response includes migration status:
```json
{
  "checks": {
    "migrations": {
      "status": "up_to_date",
      "applied": 2,
      "pending": 0
    }
  }
}
```

### Via Application Logs
```bash
# AWS CloudWatch
aws logs tail /ecs/seva-arogya-dev --follow --filter-pattern "migration"

# Local
grep -i migration logs/app.log
```

Look for:
- `"Starting database migrations..."` - Migration process started
- `"Applying migration: 001_..."` - Specific migration being applied
- `"Migration applied successfully"` - Migration completed
- `"All migrations completed successfully"` - All done
- `"No pending migrations"` - Already up-to-date

## Migration Tracking Table

Migrations are tracked in the `schema_migrations` table:

```sql
SELECT * FROM schema_migrations ORDER BY applied_at DESC;
```

Output:
```
 id |          migration_name           |       applied_at        
----+-----------------------------------+-------------------------
  1 | 001_add_streaming_columns.sql     | 2024-01-15 10:30:00
  2 | 002_add_user_preferences.sql      | 2024-01-16 14:20:00
```

## Troubleshooting

### Migration Failed During Startup

**Symptoms**: Application starts but migration errors in logs

**Check logs**:
```bash
aws logs tail /ecs/seva-arogya-dev --filter-pattern "ERROR.*migration"
```

**Common causes**:
1. **SQL syntax error**: Fix the SQL in the migration file
2. **Permission denied**: Ensure database user has ALTER/CREATE permissions
3. **Constraint violation**: Check for existing data conflicts

**Resolution**:
1. Fix the migration file
2. Manually rollback if needed:
   ```sql
   DELETE FROM schema_migrations WHERE migration_name = '00X_failed_migration.sql';
   ```
3. Redeploy with fixed migration

### Migration Stuck/Hanging

**Symptoms**: Application startup takes very long

**Possible causes**:
- Large table alteration (e.g., adding column to millions of rows)
- Lock contention with other database operations

**Resolution**:
1. Check database locks:
   ```sql
   SELECT * FROM pg_locks WHERE NOT granted;
   ```
2. Consider running large migrations during maintenance window
3. Use `CONCURRENTLY` for index creation when possible

### Need to Skip a Migration

**Not recommended**, but if absolutely necessary:

```sql
-- Manually mark migration as applied (without running it)
INSERT INTO schema_migrations (migration_name) 
VALUES ('00X_migration_to_skip.sql');
```

### Need to Rollback a Migration

1. **Create rollback SQL** (e.g., `001_add_streaming_columns_rollback.sql`):
```sql
ALTER TABLE transcriptions
DROP COLUMN IF EXISTS session_id,
DROP COLUMN IF EXISTS streaming_job_id;
-- ... reverse all changes
```

2. **Run manually**:
```bash
python migrations/run_migration.py migrations/001_add_streaming_columns_rollback.sql
```

3. **Remove from tracking**:
```sql
DELETE FROM schema_migrations 
WHERE migration_name = '001_add_streaming_columns.sql';
```

## Best Practices

### ✅ DO

- **Test migrations locally first** before deploying
- **Make migrations idempotent** when possible (use `IF NOT EXISTS`, `IF EXISTS`)
- **Keep migrations small** and focused on one change
- **Add comments** explaining what the migration does
- **Create rollback scripts** for complex migrations
- **Use transactions** (migrations run in a transaction by default)

### ❌ DON'T

- **Don't modify applied migrations** - create a new migration instead
- **Don't delete migration files** that have been applied
- **Don't skip migration numbers** - keep them sequential
- **Don't include data migrations** with large datasets (use separate process)
- **Don't use database-specific syntax** unless necessary

## Example Migration

```sql
-- Migration: Add user notification preferences
-- Date: 2024-01-20
-- Description: Adds columns to track user notification settings

-- Add columns with defaults
ALTER TABLE users
ADD COLUMN IF NOT EXISTS email_notifications BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS sms_notifications BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS notification_frequency VARCHAR(20) DEFAULT 'daily';

-- Create index for common queries
CREATE INDEX IF NOT EXISTS idx_users_email_notifications 
ON users(email_notifications) 
WHERE email_notifications = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN users.email_notifications IS 'User preference for email notifications';
COMMENT ON COLUMN users.sms_notifications IS 'User preference for SMS notifications';
COMMENT ON COLUMN users.notification_frequency IS 'Frequency: immediate, daily, weekly';
```

## Manual Migration (Emergency)

If automatic migrations fail and you need to run manually:

```bash
# Connect to database
psql -h your-db-host -U your-db-user -d your-db-name

# Run migration SQL
\i migrations/00X_your_migration.sql

# Mark as applied
INSERT INTO schema_migrations (migration_name) 
VALUES ('00X_your_migration.sql');
```

## Monitoring

Set up alerts for:
- Migration failures (check logs for "Failed to apply migration")
- Pending migrations in production (check health endpoint)
- Long-running migrations (>5 minutes)

## Support

For migration issues:
1. Check application logs first
2. Verify database connectivity and permissions
3. Review migration SQL for syntax errors
4. Contact DevOps team with:
   - Migration file name
   - Error message from logs
   - Database version and configuration
