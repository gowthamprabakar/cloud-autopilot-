-- Cloud Posture Copilot — Postgres bootstrap
-- Sprint 0: extensions + placeholder schema.
-- All actual DDL is managed through Alembic migrations.
-- This file only runs once on first postgres container init.

-- UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pg_trgm for fast text search on findings/resources (Phase 2+)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Confirm init
SELECT 'Cloud Posture Copilot postgres initialised' AS status;
