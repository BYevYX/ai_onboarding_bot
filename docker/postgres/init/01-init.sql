-- Initialize the onboarding bot database
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create additional database for testing if needed
-- CREATE DATABASE onboarding_bot_test OWNER user;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE onboarding_bot TO user;

-- Create schema for application tables (optional, can be done via Alembic)
-- CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION user;

-- Set default search path
-- ALTER DATABASE onboarding_bot SET search_path TO app, public;

-- Log initialization completion
\echo 'Database initialization completed successfully'