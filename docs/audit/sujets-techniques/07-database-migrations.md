# Database Migrations — Alembic Guide

This guide explains how to create, apply, and troubleshoot Alembic database migrations in the crypto-bot project.

## Overview

Alembic is a lightweight SQLAlchemy migration tool that manages schema changes to TimescaleDB. All ORM models are defined in `src/shared/db_models.py`, and migrations are generated automatically.

## Quick Start

### Create a New Migration

1. **Modify the ORM model** in `src/shared/db_models.py`:
   ```python
   class UserOrm(Base):
       __tablename__ = "users"
       id = Column(UUID, primary_key=True)
       email = Column(String(254), unique=True, nullable=False)
       created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
       # NEW COLUMN
       last_login_at = Column(DateTime(timezone=True), nullable=True)
   ```

2. **Auto-generate the migration**:
   ```bash
   cd /home/app
   alembic revision --autogenerate -m "add last_login_at to users"
   ```
   Output:
   ```
   Generating /app/alembic/versions/2026_03_12_1234_add_last_login_at_to_users.py ... done
   ```

3. **Review the generated migration**:
   ```bash
   cat alembic/versions/2026_03_12_1234_add_last_login_at_to_users.py
   ```
   Expected:
   ```python
   def upgrade() -> None:
       op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

   def downgrade() -> None:
       op.drop_column('users', 'last_login_at')
   ```

4. **Edit if needed** — Alembic auto-generates most changes correctly, but complex operations may require manual adjustment.

5. **Test the migration** (local dev):
   ```bash
   alembic upgrade head
   ```
   Then verify the schema with psql:
   ```bash
   docker-compose exec timescaledb psql -U postgres -d cryptobot -c "\d users"
   ```

6. **Commit the migration**:
   ```bash
   git add alembic/versions/2026_03_12_1234_*.py
   git commit -m "migrate: add last_login_at to users table"
   ```

## Common Migration Tasks

### Add a Column

```python
# ORM change
class OHLCVOrm(Base):
    ...
    volume_change_pct = Column(Float, nullable=True)

# Generated migration
def upgrade() -> None:
    op.add_column('crypto_price', 
        sa.Column('volume_change_pct', sa.Float(), nullable=True))
```

### Rename a Column

```python
# ORM change: just change the property name and the column name
class OHLCVOrm(Base):
    volume_usd = Column('volume_usd', Float)  # was 'volume'

# Manual migration (auto-generate won't detect renaming):
def upgrade() -> None:
    op.alter_column('crypto_price', 'volume', new_column_name='volume_usd')

def downgrade() -> None:
    op.alter_column('crypto_price', 'volume_usd', new_column_name='volume')
```

### Create an Index

```python
# ORM change
class OHLCVOrm(Base):
    __table_args__ = (
        Index('ix_ohlcv_symbol_timestamp', 'symbol', 'timestamp'),
    )

# Generated migration creates the index automatically
def upgrade() -> None:
    op.create_index('ix_ohlcv_symbol_timestamp', 'crypto_price', 
                    ['symbol', 'timestamp'], existing_ok=True)
```

### Convert a Table to TimescaleDB Hypertable

For time-series tables (OHLCV, indicators, signals), you may need to create a hypertable:

```python
def upgrade() -> None:
    # After the base table is created
    op.execute("""
        SELECT create_hypertable('crypto_price', 'timestamp', 
                                  if_not_exists => TRUE);
    """)
    # Add retention policy (keep 2 years)
    op.execute("""
        SELECT add_retention_policy('crypto_price', '730 days', 
                                    if_not_exists => TRUE);
    """)

def downgrade() -> None:
    # Remove retention policy
    op.execute("SELECT remove_retention_policy('crypto_price', if_exists => TRUE);")
    # Hypertable stays (cannot easily revert without data loss)
```

## Troubleshooting

### Migration Conflicts

If two developers create migrations at the same time:

```bash
# Check current head
alembic current

# View all revisions
alembic history

# If heads diverged, merge manually:
# Edit the new migration to `depends_on` both parents
# in the down_revision
```

### Rollback a Migration

```bash
# See what's applied
alembic current

# Rollback one step
alembic downgrade -1

# Rollback to a specific version
alembic downgrade 2026_03_12_1234
```

### Test a Migration Without Applying

```bash
# View the SQL without running it
alembic upgrade head --sql
```

### Failed Migration (Partial Application)

If a migration fails midway and leaves the DB in a bad state:

1. **Identify the failed revision**:
   ```bash
   alembic current  # Shows last applied
   ```

2. **Rollback carefully**:
   ```bash
   # Downgrade to before the failed migration
   alembic downgrade -1
   ```

3. **Fix the migration** and test locally
4. **Reapply**:
   ```bash
   alembic upgrade head
   ```

## Best Practices

1. **Always test locally first**: Run migrations on your local Docker Compose setup before production
2. **Separate DDL and DML**: Avoid mixing data changes with schema changes in one migration
3. **Make migrations reversible**: Always implement `downgrade()` so you can rollback
4. **Write migration descriptions**: Include a clear `-m` message explaining the change
5. **Review auto-generated SQL**: Alembic is smart but not perfect — check the generated SQL
6. **One logical change per migration**: Don't mix unrelated schema changes
7. **Keep migrations small**: Easier to understand, debug, and rollback

## CI/CD Integration

Migrations run automatically in the deployment pipeline:

```bash
# In Ansible deploy playbook (already configured)
docker compose exec -T timescaledb alembic upgrade head
```

To skip auto-migration (risky, manual only):

```bash
# In VPS, manually control migrations
docker compose exec timescaledb alembic upgrade head
docker compose exec timescaledb alembic downgrade -1  # if needed
```

## Production Checklist

Before deploying a migration to production:

- [ ] Tested migration locally on complete dataset
- [ ] Rollback procedure tested and documented
- [ ] Backward-compatible schema (new columns nullable, new tables optional)
- [ ] No locking operations on large tables (downtime risk)
- [ ] Data backup created (via `pg_dump` before running)
- [ ] Migration is reversible (downgrade() implemented)
- [ ] Performance impact assessed (new indexes, large data moves)

---

*See also: [PRODUCTION_RUNBOOK.md](./PRODUCTION_RUNBOOK.md) — Backup and Recovery procedures*
