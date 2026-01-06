-- Migration: 001_create_bevigil_enrichment
-- Created: 2026-01-06
-- Description: Create main BeVigil enrichment table

CREATE TABLE bevigil_enrichment (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Key to apps table
    app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    bundle_id VARCHAR(255) NOT NULL,

    -- Processing Status
    enrichment_status VARCHAR(50) DEFAULT 'pending'
        CHECK (enrichment_status IN ('pending', 'processing', 'completed', 'failed', 'not_found', 'no_credits')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_enriched_at TIMESTAMPTZ,

    -- Security Severity Rating
    severity_grade VARCHAR(5),
    severity_score NUMERIC(4,2),

    -- Issue Counts by Category
    vuln_total INTEGER DEFAULT 0,
    vuln_high INTEGER DEFAULT 0,
    vuln_medium INTEGER DEFAULT 0,
    vuln_low INTEGER DEFAULT 0,

    secrets_total INTEGER DEFAULT 0,
    secrets_high INTEGER DEFAULT 0,
    secrets_medium INTEGER DEFAULT 0,
    secrets_low INTEGER DEFAULT 0,

    assets_total INTEGER DEFAULT 0,

    manifest_total INTEGER DEFAULT 0,
    manifest_high INTEGER DEFAULT 0,
    manifest_medium INTEGER DEFAULT 0,
    manifest_low INTEGER DEFAULT 0,

    -- Asset Counts
    host_count INTEGER DEFAULT 0,
    url_count INTEGER DEFAULT 0,
    s3_bucket_count INTEGER DEFAULT 0,
    firebase_url_count INTEGER DEFAULT 0,
    email_count INTEGER DEFAULT 0,
    ip_address_count INTEGER DEFAULT 0,
    rest_api_count INTEGER DEFAULT 0,
    file_path_count INTEGER DEFAULT 0,

    -- Metadata Counts
    third_party_lib_count INTEGER DEFAULT 0,
    tracker_count INTEGER DEFAULT 0,

    -- Certificate Information
    apk_signed BOOLEAN,
    v1_signature BOOLEAN,
    v2_signature BOOLEAN,
    v3_signature BOOLEAN,
    cert_issuer TEXT,
    cert_subject TEXT,
    cert_valid_from TIMESTAMPTZ,
    cert_valid_to TIMESTAMPTZ,
    cert_sha256 VARCHAR(64),

    -- Extracted Arrays
    hosts TEXT[],
    urls TEXT[],
    s3_buckets TEXT[],
    firebase_urls TEXT[],
    emails TEXT[],
    ip_addresses TEXT[],
    rest_apis TEXT[],
    file_paths TEXT[],
    third_party_libs TEXT[],
    trackers TEXT[],

    -- Raw API Responses
    all_assets_response JSONB,
    report_response JSONB,

    -- Constraints
    UNIQUE(app_id),
    UNIQUE(bundle_id)
);

-- Indexes
CREATE INDEX idx_bevigil_enrichment_status ON bevigil_enrichment(enrichment_status);
CREATE INDEX idx_bevigil_enrichment_app_id ON bevigil_enrichment(app_id);
CREATE INDEX idx_bevigil_enrichment_severity_grade ON bevigil_enrichment(severity_grade);
CREATE INDEX idx_bevigil_enrichment_severity_score ON bevigil_enrichment(severity_score DESC);
CREATE INDEX idx_bevigil_enrichment_vuln_high ON bevigil_enrichment(vuln_high DESC) WHERE vuln_high > 0;

CREATE INDEX idx_bevigil_enrichment_hosts ON bevigil_enrichment USING GIN(hosts);
CREATE INDEX idx_bevigil_enrichment_emails ON bevigil_enrichment USING GIN(emails);
CREATE INDEX idx_bevigil_enrichment_s3_buckets ON bevigil_enrichment USING GIN(s3_buckets);
CREATE INDEX idx_bevigil_enrichment_third_party_libs ON bevigil_enrichment USING GIN(third_party_libs);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_bevigil_enrichment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_bevigil_enrichment_updated_at
    BEFORE UPDATE ON bevigil_enrichment
    FOR EACH ROW
    EXECUTE FUNCTION update_bevigil_enrichment_timestamp();

-- Comments
COMMENT ON TABLE bevigil_enrichment IS 'BeVigil OSINT enrichment data for Android apps';
COMMENT ON COLUMN bevigil_enrichment.severity_grade IS 'Overall security grade: A (best) to F (worst)';
COMMENT ON COLUMN bevigil_enrichment.severity_score IS 'Numeric security score: 0.0 (best) to 10.0 (worst)';
COMMENT ON COLUMN bevigil_enrichment.enrichment_status IS 'Processing status: pending, processing, completed, failed, not_found, no_credits';
