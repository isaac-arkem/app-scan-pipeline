-- Migration: 002_create_bevigil_vulnerabilities
-- Created: 2026-01-06
-- Description: Create BeVigil vulnerabilities table for normalized vulnerability data

CREATE TABLE bevigil_vulnerabilities (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    enrichment_id INTEGER NOT NULL REFERENCES bevigil_enrichment(id) ON DELETE CASCADE,
    app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,

    -- Vulnerability Classification
    vuln_type VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL
        CHECK (category IN ('vuln', 'secrets', 'manifest', 'assets')),

    -- CWE Information
    cwe_id VARCHAR(20),
    cwe_name TEXT,

    -- Severity & Scoring
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    cvss_score NUMERIC(3,1),

    -- Vulnerability Details
    description TEXT,
    mitigation TEXT,
    reference TEXT,

    -- Match Information
    match_count INTEGER DEFAULT 1,
    sample_matches JSONB,
    affected_files TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(enrichment_id, vuln_type, category)
);

-- Indexes
CREATE INDEX idx_bevigil_vuln_enrichment_id ON bevigil_vulnerabilities(enrichment_id);
CREATE INDEX idx_bevigil_vuln_app_id ON bevigil_vulnerabilities(app_id);
CREATE INDEX idx_bevigil_vuln_severity ON bevigil_vulnerabilities(severity);
CREATE INDEX idx_bevigil_vuln_cwe_id ON bevigil_vulnerabilities(cwe_id);
CREATE INDEX idx_bevigil_vuln_cvss ON bevigil_vulnerabilities(cvss_score DESC) WHERE cvss_score > 0;
CREATE INDEX idx_bevigil_vuln_category ON bevigil_vulnerabilities(category);
CREATE INDEX idx_bevigil_vuln_type ON bevigil_vulnerabilities(vuln_type);
CREATE INDEX idx_bevigil_vuln_severity_cvss ON bevigil_vulnerabilities(severity, cvss_score DESC);

-- Comments
COMMENT ON TABLE bevigil_vulnerabilities IS 'Individual vulnerability findings from BeVigil security scans';
COMMENT ON COLUMN bevigil_vulnerabilities.category IS 'Issue category: vuln (vulnerabilities), secrets (exposed credentials), manifest (Android manifest issues), assets (exposed assets)';
COMMENT ON COLUMN bevigil_vulnerabilities.cwe_id IS 'Common Weakness Enumeration ID';
COMMENT ON COLUMN bevigil_vulnerabilities.cvss_score IS 'Common Vulnerability Scoring System score (0.0-10.0)';
