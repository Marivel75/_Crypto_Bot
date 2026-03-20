# Database Migration

Create and apply database migrations using Alembic.

## Steps
1. Check current migration status: `cd /Users/amaury/Desktop/jules/crypto-bot && alembic current`
2. If creating new migration: `alembic revision --autogenerate -m "$ARGUMENTS"`
3. Review generated migration file
4. Apply migration: `alembic upgrade head`
5. Verify: `alembic current`
