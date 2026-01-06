# BeVigil App Enrichment - Implementation Plan

## Executive Summary

This plan outlines the implementation of an app data enrichment system using the BeVigil OSINT API. The system will enrich Android app data from the `apps` table in the Supabase arkuts project, storing security and asset intelligence in a new `bevigil_enrichment` table.

**Key Constraint:** BeVigil only analyzes Android APKs. Out of 2,409 apps in the database, only **89 are Android apps** that can be enriched.

---

## 1. BeVigil API Analysis

### Available Endpoints

| Endpoint | Description | Data Returned |
|----------|-------------|---------------|
| `/api/{package_id}/all-assets/` | All extracted assets | URLs, hosts, IPs, emails, S3 buckets, Firebase URLs, REST APIs |
| `/api/{package_id}/hosts/` | Unique hostnames | Array of hostnames |
| `/api/{package_id}/S3-buckets/` | S3 bucket URLs | Array of S3 URLs |
| `/api/{package_id}/report/` | Full security report | Vulnerabilities, CWE data, severity scores, file locations |
| `/api/{package_id}/wordlist/` | Extracted keywords | Wordlist for fuzzing |
| `/api/{package_id}/params/` | URL parameters | Key-value pairs from URLs |

### Authentication
- Header: `X-Access-Token: <API_KEY>`
- Base URL: `https://osint.bevigil.com`

### Rate Limiting & Credits
- Rate limit enforced (HTTP 422 on exceed)
- Credit-based system (HTTP 402 when depleted)

### Recommended API Strategy
**Primary:** Use `/all-assets/` endpoint only
- Returns comprehensive data with 1 API credit per app
- Includes: URLs, hosts, IPs, emails, S3 buckets, Firebase URLs, REST APIs

**Optional:** Add `/report/` for security analysis
- Adds vulnerability scanning data, CWE classifications, severity scores
- Use only if security scoring is a priority

---

## 2. Database Schema Design

### New Table: `bevigil_enrichment`

```sql
CREATE TABLE bevigil_enrichment (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    bundle_id VARCHAR(255) NOT NULL,

    -- Processing Status
    enrichment_status VARCHAR(50) DEFAULT 'pending'
        CHECK (enrichment_status IN ('pending', 'processing', 'completed', 'failed', 'not_found')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_enriched_at TIMESTAMPTZ,

    -- Asset Counts (for quick filtering/dashboards)
    host_count INTEGER DEFAULT 0,
    s3_bucket_count INTEGER DEFAULT 0,
    url_count INTEGER DEFAULT 0,
    email_count INTEGER DEFAULT 0,
    ip_address_count INTEGER DEFAULT 0,
    firebase_url_count INTEGER DEFAULT 0,
    rest_api_count INTEGER DEFAULT 0,

    -- Security Metrics (from /report/ endpoint)
    security_score NUMERIC(5,2),
    total_issue_count INTEGER DEFAULT 0,
    high_severity_count INTEGER DEFAULT 0,
    medium_severity_count INTEGER DEFAULT 0,
    low_severity_count INTEGER DEFAULT 0,

    -- Raw API Responses (JSONB for flexibility)
    all_assets_response JSONB,
    report_response JSONB,

    -- Extracted Arrays (for efficient querying)
    hosts TEXT[],
    s3_buckets TEXT[],
    emails TEXT[],
    ip_addresses TEXT[],
    firebase_urls TEXT[],
    urls TEXT[],
    rest_apis TEXT[],
    file_paths TEXT[],

    -- Constraints
    UNIQUE(app_id),
    UNIQUE(bundle_id)
);

-- Indexes for common queries
CREATE INDEX idx_bevigil_enrichment_status ON bevigil_enrichment(enrichment_status);
CREATE INDEX idx_bevigil_enrichment_app_id ON bevigil_enrichment(app_id);
CREATE INDEX idx_bevigil_enrichment_hosts ON bevigil_enrichment USING GIN(hosts);
CREATE INDEX idx_bevigil_enrichment_emails ON bevigil_enrichment USING GIN(emails);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_bevigil_enrichment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_bevigil_enrichment_timestamp
    BEFORE UPDATE ON bevigil_enrichment
    FOR EACH ROW
    EXECUTE FUNCTION update_bevigil_enrichment_timestamp();
```

---

## 3. Project Structure

```
App_Enrichment/
├── README.md                      # Project documentation
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore
├── swagger.json                   # BeVigil API spec (existing)
│
├── src/
│   ├── __init__.py
│   ├── config.py                  # Configuration management
│   ├── bevigil_client.py          # BeVigil API client with rate limiting
│   ├── supabase_client.py         # Database operations
│   ├── enrichment_service.py      # Main enrichment orchestration
│   └── models.py                  # Pydantic data models
│
├── scripts/
│   ├── run_enrichment.py          # CLI entry point
│   ├── setup_database.py          # Run migrations
│   └── check_status.py            # View enrichment progress
│
├── migrations/
│   └── 001_create_bevigil_enrichment.sql
│
└── tests/
    ├── test_bevigil_client.py
    └── test_enrichment_service.py
```

---

## 4. Implementation Components

### 4.1 Configuration (`src/config.py`)
```python
# Environment variables:
BEVIGIL_API_KEY          # Required: BeVigil API access token
SUPABASE_URL             # Required: Supabase project URL
SUPABASE_SERVICE_KEY     # Required: Supabase service role key
BATCH_SIZE               # Optional: Apps per batch (default: 10)
REQUEST_DELAY            # Optional: Seconds between API calls (default: 1.0)
MAX_RETRIES              # Optional: Retry attempts on failure (default: 3)
INCLUDE_REPORT           # Optional: Also fetch /report/ endpoint (default: false)
```

### 4.2 BeVigil Client (`src/bevigil_client.py`)
- HTTP client with retry logic
- Rate limit handling (exponential backoff on 422)
- Credit exhaustion detection (402 handling)
- Response validation and parsing

### 4.3 Supabase Client (`src/supabase_client.py`)
- Fetch Android apps pending enrichment
- Upsert enrichment records
- Update processing status
- Query enrichment statistics

### 4.4 Enrichment Service (`src/enrichment_service.py`)
- Batch processing orchestration
- Parallel processing with semaphores
- Progress tracking and logging
- Graceful shutdown handling

---

## 5. Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENRICHMENT PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. FETCH CANDIDATES                                            │
│     ├─ Query apps WHERE platform = 'Android'                    │
│     └─ LEFT JOIN bevigil_enrichment WHERE status != 'completed' │
│                                                                 │
│  2. BATCH PROCESSING (10 apps at a time)                        │
│     ├─ For each app:                                            │
│     │   ├─ Set status = 'processing'                            │
│     │   ├─ Call BeVigil /all-assets/ API                        │
│     │   ├─ (Optional) Call BeVigil /report/ API                 │
│     │   ├─ Parse and extract data                               │
│     │   ├─ Upsert to bevigil_enrichment                         │
│     │   └─ Set status = 'completed' or 'failed'                 │
│     └─ Delay between requests (rate limiting)                   │
│                                                                 │
│  3. ERROR HANDLING                                              │
│     ├─ 404: Mark as 'not_found' (app not in BeVigil DB)        │
│     ├─ 422: Exponential backoff, retry                          │
│     ├─ 402: Stop processing (credits exhausted)                 │
│     └─ 5xx: Retry with backoff                                  │
│                                                                 │
│  4. COMPLETION                                                  │
│     └─ Log statistics, remaining apps, errors                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Usage Examples

### Running the Enrichment
```bash
# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
pip install -r requirements.txt

# Run database migration
python scripts/setup_database.py

# Start enrichment (default: all-assets only)
python scripts/run_enrichment.py

# Include security reports
python scripts/run_enrichment.py --include-report

# Process specific batch size
python scripts/run_enrichment.py --batch-size 5

# Check progress
python scripts/check_status.py
```

### Querying Enriched Data
```sql
-- Apps with exposed S3 buckets
SELECT a.app_name, a.bundle_id, be.s3_buckets, be.s3_bucket_count
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE be.s3_bucket_count > 0;

-- Apps with email addresses found
SELECT a.app_name, be.emails
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE array_length(be.emails, 1) > 0;

-- High-risk apps (if report data included)
SELECT a.app_name, be.high_severity_count, be.security_score
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE be.high_severity_count > 0
ORDER BY be.high_severity_count DESC;

-- Enrichment progress
SELECT
    enrichment_status,
    COUNT(*) as count
FROM bevigil_enrichment
GROUP BY enrichment_status;
```

---

## 7. Estimated Effort

| Phase | Tasks | Estimate |
|-------|-------|----------|
| **Phase 1: Setup** | Project structure, config, migrations | 1-2 hours |
| **Phase 2: Core** | BeVigil client, Supabase client | 2-3 hours |
| **Phase 3: Service** | Enrichment service, CLI | 2-3 hours |
| **Phase 4: Testing** | Unit tests, integration tests | 1-2 hours |
| **Phase 5: Run** | Initial enrichment of 89 apps | ~2-3 mins |

**Total: ~8-10 hours development, ~3 mins runtime**

---

## 8. Considerations & Risks

### API Credits
- 89 Android apps to enrich
- Using /all-assets/ only: 89 credits
- Adding /report/: 178 credits total
- Ensure sufficient BeVigil credits before running

### Rate Limiting
- Built-in delays (1 second default)
- Exponential backoff on 422 errors
- Graceful handling of credit exhaustion

### Data Quality
- Some apps may not exist in BeVigil database (404)
- Mark as 'not_found' rather than 'failed'
- Track success rate in logs

### Incremental Updates
- UNIQUE constraint on app_id prevents duplicates
- Re-running updates existing records
- Can add schedule for periodic re-enrichment

---

## 9. Next Steps

1. **Approve this plan**
2. **Confirm BeVigil API key availability**
3. **Decide on /report/ inclusion** (additional credits but adds security data)
4. **Proceed with implementation**

---

## 10. Questions for Clarification

1. Do you have a BeVigil API key, or do we need to set one up?
2. Should we include the `/report/` endpoint for security vulnerability data?
3. Any preference on Python version (3.9+ recommended)?
4. Should the enrichment run as a one-time script or be deployable as a scheduled job?
