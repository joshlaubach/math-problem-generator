# Operations Runbook

## Database Backups (Railway PostgreSQL)

### Enable Automatic Backups

1. Log into [Railway Dashboard](https://railway.app)
2. Select the **Gradient** project
3. Click the **PostgreSQL** plugin
4. Go to **Backups** tab
5. Enable **Daily Backups** with **7-day retention**

### Manual Backup (pg_dump)

```bash
pg_dump "$DATABASE_URL" --no-acl --no-owner -Fc -f backup_$(date +%Y%m%d).dump
```

Upload to a safe location (S3, Google Drive) before running schema migrations.

### Restore from Backup

```bash
# Drop all connections first
psql "$DATABASE_URL" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();"

# Restore
pg_restore --clean --no-acl --no-owner -d "$DATABASE_URL" backup_YYYYMMDD.dump
```

### Alembic Migrations

```bash
cd apps/api

# Check current migration state
alembic current

# Preview what would change
alembic upgrade head --sql

# Apply migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

Always take a manual backup before running `alembic upgrade head` in production.

## Incident Response

### API is down (Railway)

1. Check Railway dashboard for deploy errors
2. Check `/health` endpoint — `{"db": false}` means DB connection failure
3. Check Railway PostgreSQL plugin status
4. If DB is up but API is down: check Railway logs for the Python traceback

### Session credits lost after deploy

Railway SIGTERM sends a shutdown signal; the lifespan block in `api.py` attempts to end active sessions cleanly with a 5s timeout. If credits were still lost:

1. Query `credit_usage` table for sessions with `status = 'active'` that are older than the deploy time
2. Manually restore credits: `UPDATE credit_usage SET status = 'restored' WHERE ...`
3. Set `REDIS_URL` in Railway to persist session state across deploys
