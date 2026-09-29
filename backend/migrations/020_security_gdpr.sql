-- Migration 020: Security & GDPR tables
-- Run on Supabase SQL editor

-- Consent tracking for GDPR compliance
CREATE TABLE user_consents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  consent_type TEXT NOT NULL CHECK (consent_type IN ('data_processing', 'data_sharing', 'marketing')),
  granted BOOLEAN NOT NULL DEFAULT false,
  granted_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  ip_address TEXT,
  version TEXT NOT NULL DEFAULT '1.0',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, consent_type)
);

-- Deletion audit log for GDPR right to erasure
CREATE TABLE deletion_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  deleted_by UUID NOT NULL REFERENCES profiles(id),
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  entity_summary JSONB,
  deleted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Security audit log
CREATE TABLE audit_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES profiles(id),
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id UUID,
  ip_address TEXT,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

-- RLS policies (backend uses service_role to bypass, but defense-in-depth)
ALTER TABLE user_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE deletion_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Users can read their own consents
CREATE POLICY "Users can read own consents" ON user_consents
  FOR SELECT USING (auth.uid() = user_id);

-- Users can update their own consents
CREATE POLICY "Users can update own consents" ON user_consents
  FOR ALL USING (auth.uid() = user_id);
