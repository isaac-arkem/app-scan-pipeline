# BeVigil Enrichment Database Schema

## Overview

This schema consists of **two tables**:
1. `bevigil_enrichment` - Main enrichment data (assets, metadata, security scores)
2. `bevigil_vulnerabilities` - Normalized vulnerability findings with CWE/CVSS data

This design allows efficient querying of vulnerabilities across all apps while keeping the main enrichment table clean.

---

## Table 1: `bevigil_enrichment`

Main table storing enrichment results and extracted assets.

```sql
-- ============================================
-- TABLE: bevigil_enrichment
-- Main enrichment data from BeVigil API
-- ============================================

CREATE TABLE bevigil_enrichment (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Key to apps table
    app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    bundle_id VARCHAR(255) NOT NULL,

    -- ============================================
    -- Processing Status
    -- ============================================
    enrichment_status VARCHAR(50) DEFAULT 'pending'
        CHECK (enrichment_status IN ('pending', 'processing', 'completed', 'failed', 'not_found', 'no_credits')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- ============================================
    -- Timestamps
    -- ============================================
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_enriched_at TIMESTAMPTZ,

    -- ============================================
    -- Security Severity Rating (from report)
    -- ============================================
    severity_grade VARCHAR(5),           -- A, B, C, D, E, F
    severity_score NUMERIC(4,2),         -- 0.0 - 10.0

    -- ============================================
    -- Issue Counts by Category
    -- ============================================
    -- Vulnerabilities
    vuln_total INTEGER DEFAULT 0,
    vuln_high INTEGER DEFAULT 0,
    vuln_medium INTEGER DEFAULT 0,
    vuln_low INTEGER DEFAULT 0,

    -- Secrets (exposed credentials, keys, etc.)
    secrets_total INTEGER DEFAULT 0,
    secrets_high INTEGER DEFAULT 0,
    secrets_medium INTEGER DEFAULT 0,
    secrets_low INTEGER DEFAULT 0,

    -- Assets (URLs, hosts, etc. - informational)
    assets_total INTEGER DEFAULT 0,

    -- Manifest issues
    manifest_total INTEGER DEFAULT 0,
    manifest_high INTEGER DEFAULT 0,
    manifest_medium INTEGER DEFAULT 0,
    manifest_low INTEGER DEFAULT 0,

    -- ============================================
    -- Asset Counts (quick reference)
    -- ============================================
    host_count INTEGER DEFAULT 0,
    url_count INTEGER DEFAULT 0,
    s3_bucket_count INTEGER DEFAULT 0,
    firebase_url_count INTEGER DEFAULT 0,
    email_count INTEGER DEFAULT 0,
    ip_address_count INTEGER DEFAULT 0,
    rest_api_count INTEGER DEFAULT 0,
    file_path_count INTEGER DEFAULT 0,

    -- ============================================
    -- Metadata Counts
    -- ============================================
    third_party_lib_count INTEGER DEFAULT 0,
    tracker_count INTEGER DEFAULT 0,

    -- ============================================
    -- Certificate Information
    -- ============================================
    apk_signed BOOLEAN,
    v1_signature BOOLEAN,
    v2_signature BOOLEAN,
    v3_signature BOOLEAN,
    cert_issuer TEXT,
    cert_subject TEXT,
    cert_valid_from TIMESTAMPTZ,
    cert_valid_to TIMESTAMPTZ,
    cert_sha256 VARCHAR(64),

    -- ============================================
    -- Extracted Arrays (for efficient querying)
    -- ============================================
    hosts TEXT[],
    urls TEXT[],
    s3_buckets TEXT[],
    firebase_urls TEXT[],
    emails TEXT[],
    ip_addresses TEXT[],
    rest_apis TEXT[],
    file_paths TEXT[],

    -- Third-party libraries (names only)
    third_party_libs TEXT[],

    -- Trackers detected
    trackers TEXT[],

    -- ============================================
    -- Raw API Responses (for debugging/full data)
    -- ============================================
    all_assets_response JSONB,
    report_response JSONB,

    -- ============================================
    -- Constraints
    -- ============================================
    UNIQUE(app_id),
    UNIQUE(bundle_id)
);

-- ============================================
-- Indexes
-- ============================================
CREATE INDEX idx_bevigil_enrichment_status ON bevigil_enrichment(enrichment_status);
CREATE INDEX idx_bevigil_enrichment_app_id ON bevigil_enrichment(app_id);
CREATE INDEX idx_bevigil_enrichment_severity_grade ON bevigil_enrichment(severity_grade);
CREATE INDEX idx_bevigil_enrichment_severity_score ON bevigil_enrichment(severity_score DESC);
CREATE INDEX idx_bevigil_enrichment_vuln_high ON bevigil_enrichment(vuln_high DESC) WHERE vuln_high > 0;

-- GIN indexes for array columns
CREATE INDEX idx_bevigil_enrichment_hosts ON bevigil_enrichment USING GIN(hosts);
CREATE INDEX idx_bevigil_enrichment_emails ON bevigil_enrichment USING GIN(emails);
CREATE INDEX idx_bevigil_enrichment_s3_buckets ON bevigil_enrichment USING GIN(s3_buckets);
CREATE INDEX idx_bevigil_enrichment_third_party_libs ON bevigil_enrichment USING GIN(third_party_libs);

-- ============================================
-- Trigger for updated_at
-- ============================================
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

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE bevigil_enrichment IS 'BeVigil OSINT enrichment data for Android apps';
COMMENT ON COLUMN bevigil_enrichment.severity_grade IS 'Overall security grade: A (best) to F (worst)';
COMMENT ON COLUMN bevigil_enrichment.severity_score IS 'Numeric security score: 0.0 (best) to 10.0 (worst)';
COMMENT ON COLUMN bevigil_enrichment.enrichment_status IS 'Processing status: pending, processing, completed, failed, not_found, no_credits';
```

---

## Table 2: `bevigil_vulnerabilities`

Normalized table for individual vulnerability findings with full CWE/CVSS details.

```sql
-- ============================================
-- TABLE: bevigil_vulnerabilities
-- Individual vulnerability findings from BeVigil report
-- ============================================

CREATE TABLE bevigil_vulnerabilities (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    enrichment_id INTEGER NOT NULL REFERENCES bevigil_enrichment(id) ON DELETE CASCADE,
    app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,

    -- ============================================
    -- Vulnerability Classification
    -- ============================================
    vuln_type VARCHAR(100) NOT NULL,     -- e.g., "WebView ignores SSL errors"
    category VARCHAR(50) NOT NULL,        -- vuln, secrets, manifest, assets

    -- ============================================
    -- CWE Information
    -- ============================================
    cwe_id VARCHAR(20),                   -- e.g., "295"
    cwe_name TEXT,                        -- e.g., "Improper Certificate Validation"

    -- ============================================
    -- Severity & Scoring
    -- ============================================
    severity VARCHAR(20) NOT NULL         -- high, medium, low
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    cvss_score NUMERIC(3,1),              -- 0.0 - 10.0

    -- ============================================
    -- Vulnerability Details
    -- ============================================
    description TEXT,                     -- Full description of the issue
    mitigation TEXT,                      -- Recommended fix
    reference TEXT,                       -- External reference URL

    -- ============================================
    -- Match Information
    -- ============================================
    match_count INTEGER DEFAULT 1,        -- Number of occurrences

    -- Sample matches (first few occurrences)
    sample_matches JSONB,                 -- Array of {filename, preview, is_tpl, spans}

    -- ============================================
    -- Affected Files (extracted for querying)
    -- ============================================
    affected_files TEXT[],                -- List of affected file paths

    -- ============================================
    -- Timestamps
    -- ============================================
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- ============================================
    -- Constraints
    -- ============================================
    UNIQUE(enrichment_id, vuln_type, category)
);

-- ============================================
-- Indexes
-- ============================================
CREATE INDEX idx_bevigil_vuln_enrichment_id ON bevigil_vulnerabilities(enrichment_id);
CREATE INDEX idx_bevigil_vuln_app_id ON bevigil_vulnerabilities(app_id);
CREATE INDEX idx_bevigil_vuln_severity ON bevigil_vulnerabilities(severity);
CREATE INDEX idx_bevigil_vuln_cwe_id ON bevigil_vulnerabilities(cwe_id);
CREATE INDEX idx_bevigil_vuln_cvss ON bevigil_vulnerabilities(cvss_score DESC) WHERE cvss_score > 0;
CREATE INDEX idx_bevigil_vuln_category ON bevigil_vulnerabilities(category);
CREATE INDEX idx_bevigil_vuln_type ON bevigil_vulnerabilities(vuln_type);

-- Composite index for common queries
CREATE INDEX idx_bevigil_vuln_severity_cvss ON bevigil_vulnerabilities(severity, cvss_score DESC);

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE bevigil_vulnerabilities IS 'Individual vulnerability findings from BeVigil security scans';
COMMENT ON COLUMN bevigil_vulnerabilities.category IS 'Issue category: vuln (vulnerabilities), secrets (exposed credentials), manifest (Android manifest issues), assets (exposed assets)';
COMMENT ON COLUMN bevigil_vulnerabilities.cwe_id IS 'Common Weakness Enumeration ID';
COMMENT ON COLUMN bevigil_vulnerabilities.cvss_score IS 'Common Vulnerability Scoring System score (0.0-10.0)';
```

---

## Example Queries

### High-Risk Apps
```sql
-- Apps with high-severity vulnerabilities
SELECT
    a.app_name,
    a.bundle_id,
    be.severity_grade,
    be.severity_score,
    be.vuln_high,
    be.vuln_medium
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE be.vuln_high > 0
ORDER BY be.severity_score DESC;
```

### Vulnerability Details
```sql
-- All high/critical vulnerabilities with CWE info
SELECT
    a.app_name,
    bv.vuln_type,
    bv.cwe_id,
    bv.cwe_name,
    bv.severity,
    bv.cvss_score,
    bv.description,
    bv.mitigation
FROM bevigil_vulnerabilities bv
JOIN apps a ON bv.app_id = a.id
WHERE bv.severity IN ('critical', 'high')
ORDER BY bv.cvss_score DESC;
```

### Apps with Specific CWE
```sql
-- Apps with SSL certificate validation issues (CWE-295)
SELECT
    a.app_name,
    bv.description,
    bv.affected_files
FROM bevigil_vulnerabilities bv
JOIN apps a ON bv.app_id = a.id
WHERE bv.cwe_id = '295';
```

### Vulnerability Summary by CWE
```sql
-- Most common vulnerabilities across all apps
SELECT
    cwe_id,
    cwe_name,
    severity,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT app_id) as affected_apps
FROM bevigil_vulnerabilities
WHERE cwe_id IS NOT NULL
GROUP BY cwe_id, cwe_name, severity
ORDER BY affected_apps DESC, occurrence_count DESC;
```

### Apps with Exposed S3 Buckets
```sql
-- Apps with S3 buckets found
SELECT
    a.app_name,
    a.developer_name,
    be.s3_buckets,
    be.s3_bucket_count
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE be.s3_bucket_count > 0
ORDER BY be.s3_bucket_count DESC;
```

### Enrichment Progress
```sql
-- Check enrichment status
SELECT
    enrichment_status,
    COUNT(*) as count
FROM bevigil_enrichment
GROUP BY enrichment_status;

-- Apps not yet enriched
SELECT COUNT(*) as pending_count
FROM apps a
LEFT JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE a.platform = 'Android'
AND (be.id IS NULL OR be.enrichment_status = 'pending');
```

### Third-Party Library Analysis
```sql
-- Most common third-party libraries
SELECT
    lib,
    COUNT(*) as usage_count
FROM bevigil_enrichment, unnest(third_party_libs) as lib
GROUP BY lib
ORDER BY usage_count DESC
LIMIT 20;
```

---

## Migration Notes

1. Run the `bevigil_enrichment` table creation first
2. Run the `bevigil_vulnerabilities` table creation second (depends on enrichment table)
3. Both tables have `ON DELETE CASCADE` - deleting an app removes all related data
4. The script will handle populating both tables during enrichment

---

## Data Flow

```
┌─────────────────┐     ┌──────────────────────┐     ┌────────────────────────┐
│   apps table    │────▶│  bevigil_enrichment  │────▶│ bevigil_vulnerabilities│
│  (89 Android)   │     │   (1 per app)        │     │  (many per app)        │
└─────────────────┘     └──────────────────────┘     └────────────────────────┘
                               │
                               │ Contains:
                               ├─ Security scores
                               ├─ Asset arrays (hosts, emails, S3, etc.)
                               ├─ Issue counts by severity
                               ├─ Certificate info
                               └─ Raw JSON responses
```
