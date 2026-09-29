-- Migration 026: Security hardening
-- - login_attempts table for DB-backed lockout tracking (replaces in-memory dict)

CREATE TABLE IF NOT EXISTS login_attempts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL,
    attempted_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address TEXT
);

CREATE INDEX idx_login_attempts_email_time ON login_attempts (email, attempted_at);
