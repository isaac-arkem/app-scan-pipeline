# Implementation Plan: BeVigil App Enrichment

## Overview

This document outlines the step-by-step implementation plan for the BeVigil app enrichment system.

---

## Phase 1: Database Setup

### 1.1 Create Tables in Supabase (arkuts project)

**Order of operations:**
1. Create `bevigil_enrichment` table (main table)
2. Create `bevigil_vulnerabilities` table (references enrichment table)
3. Create indexes for performance
4. Create update trigger for `updated_at`
5. Add table comments

**Method:** Use Supabase `apply_migration` tool to ensure migrations are tracked.

---

## Phase 2: Project Structure Setup

### 2.1 Directory Structure

```
App_Enrichment/
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
├── swagger.json                       # BeVigil API spec (existing)
├── SCHEMA.md                          # Database schema docs (existing)
├── IMPLEMENTATION_PLAN.md             # This file (existing)
│
├── src/
│   ├── __init__.py
│   ├── config.py                      # Configuration & environment variables
│   ├── models.py                      # Pydantic data models
│   ├── bevigil_client.py              # BeVigil API client
│   ├── supabase_client.py             # Supabase database operations
│   └── enrichment_service.py          # Main enrichment orchestration
│
├── scripts/
│   ├── run_enrichment.py              # CLI entry point
│   └── check_status.py                # View enrichment progress
│
└── migrations/
    ├── 001_create_bevigil_enrichment.sql
    └── 002_create_bevigil_vulnerabilities.sql
```

### 2.2 Dependencies (requirements.txt)

```
# Core
python-dotenv>=1.0.0
pydantic>=2.0.0
httpx>=0.25.0                          # Async HTTP client

# Supabase
supabase>=2.0.0

# Utilities
tenacity>=8.2.0                        # Retry logic
rich>=13.0.0                           # Pretty console output
```

---

## Phase 3: Core Components

### 3.1 Configuration (`src/config.py`)

```python
# Environment variables:
BEVIGIL_API_KEY          # Required - provided: tjhRmyI0L4Jjrz2V
SUPABASE_URL             # Required - arkuts project URL
SUPABASE_SERVICE_KEY     # Required - service role key for backend ops

# Optional with defaults:
BATCH_SIZE = 10          # Apps to process per batch
REQUEST_DELAY = 1.5      # Seconds between API calls (rate limiting)
MAX_RETRIES = 3          # Retry attempts on transient failures
REQUEST_TIMEOUT = 30     # HTTP request timeout in seconds
```

### 3.2 BeVigil Client (`src/bevigil_client.py`)

**Responsibilities:**
- Make HTTP requests to BeVigil API
- Handle authentication (X-Access-Token header)
- Implement rate limiting (delay between requests)
- Handle errors:
  - 404: App not found in BeVigil database
  - 422: Rate limit exceeded → exponential backoff
  - 402: Credits exhausted → stop processing
  - 401: Invalid API key → raise exception
  - 5xx: Server error → retry with backoff

**Endpoints to call:**
1. `/api/{package_id}/all-assets/` - Asset extraction
2. `/api/{package_id}/report/` - Security report with vulnerabilities

### 3.3 Supabase Client (`src/supabase_client.py`)

**Responsibilities:**
- Fetch Android apps pending enrichment
- Create/update enrichment records
- Insert vulnerability records (batch insert)
- Update processing status
- Query enrichment statistics

**Key methods:**
```python
def get_pending_apps(limit: int) -> list[App]
def get_enrichment_by_app_id(app_id: int) -> Optional[Enrichment]
def upsert_enrichment(data: EnrichmentData) -> int  # returns enrichment_id
def insert_vulnerabilities(vulns: list[VulnerabilityData]) -> None
def update_status(app_id: int, status: str, error: str = None) -> None
def get_enrichment_stats() -> dict
```

### 3.4 Enrichment Service (`src/enrichment_service.py`)

**Main orchestration logic:**

```
1. Query apps table for Android apps
2. LEFT JOIN with bevigil_enrichment to find:
   - Apps with no enrichment record (new)
   - Apps with status = 'pending' or 'failed' (retry)
3. Exclude apps with status = 'completed' or 'not_found'
4. Process in batches:
   a. Set status = 'processing'
   b. Call BeVigil /all-assets/ endpoint
   c. Call BeVigil /report/ endpoint
   d. Parse responses
   e. Extract assets and vulnerabilities
   f. Upsert enrichment record
   g. Insert vulnerability records
   h. Set status = 'completed'
   i. Delay before next request
5. Handle errors gracefully
6. Log progress and statistics
```

### 3.5 CLI Script (`scripts/run_enrichment.py`)

**Features:**
- Parse command-line arguments
- Display progress bar
- Show real-time statistics
- Graceful shutdown on Ctrl+C
- Summary report on completion

**Usage:**
```bash
# Process all pending apps
python scripts/run_enrichment.py

# Limit to specific number of apps
python scripts/run_enrichment.py --limit 10

# Force re-process failed apps
python scripts/run_enrichment.py --retry-failed

# Dry run (no writes)
python scripts/run_enrichment.py --dry-run
```

---

## Phase 4: Data Extraction Logic

### 4.1 From `/all-assets/` Response

Extract and store:
- `hosts[]` - Unique hostnames
- `urls[]` - Full URLs found
- `s3_buckets[]` - AWS S3 URLs (from "AWS URL" key)
- `firebase_urls[]` - Firebase URLs
- `emails[]` - Email addresses
- `ip_addresses[]` - IP addresses (from "IP Address disclosure")
- `rest_apis[]` - REST API endpoints
- `file_paths[]` - File paths

### 4.2 From `/report/` Response

**Main enrichment record:**
- `severity_grade` - from `report.severity_rating.severity_grade`
- `severity_score` - from `report.severity_rating.severity_score`
- Issue counts from `report.report_summary.issues_per_scanner_counts`
- Certificate info from `report.results_metadata.certificate`
- Third-party libs from `report.results_metadata.third_party_libs`
- Trackers from `report.results_metadata.trackers`

**Vulnerability records (separate table):**
Parse `report.results_issues.vuln[]`, `report.results_issues.secrets[]`, `report.results_issues.manifest[]`:

For each issue:
- `vuln_type` - from `type`
- `category` - vuln/secrets/manifest
- `cwe_id` - from `issue_info.cwe_id`
- `cwe_name` - from `issue_info.cwe_name`
- `severity` - from `issue_info.severity`
- `cvss_score` - from `issue_info.cvss_score`
- `description` - from `issue_info.description`
- `mitigation` - from `issue_info.mitigation`
- `reference` - from `issue_info.reference`
- `match_count` - length of `matches[]`
- `affected_files` - extracted from matches
- `sample_matches` - first 5 matches as JSONB

---

## Phase 5: Error Handling Strategy

| Error | Response | Action |
|-------|----------|--------|
| 404 Not Found | App not in BeVigil DB | Set status = 'not_found', continue |
| 422 Rate Limit | Slow down | Exponential backoff (2s, 4s, 8s...), retry |
| 402 No Credits | Credits exhausted | Set status = 'no_credits', STOP all processing |
| 401 Unauthorized | Invalid API key | Raise exception, STOP |
| 5xx Server Error | BeVigil issue | Retry up to 3 times with backoff |
| Network Error | Connection issue | Retry up to 3 times with backoff |
| Parse Error | Unexpected response | Log error, set status = 'failed', continue |

---

## Phase 6: Implementation Order

### Step 1: Database Migration
- [ ] Apply migration for `bevigil_enrichment` table
- [ ] Apply migration for `bevigil_vulnerabilities` table
- [ ] Verify tables created correctly

### Step 2: Project Files
- [ ] Create directory structure
- [ ] Create `requirements.txt`
- [ ] Create `.env.example`
- [ ] Create `.gitignore`
- [ ] Create `README.md`

### Step 3: Core Code
- [ ] Implement `src/config.py`
- [ ] Implement `src/models.py` (Pydantic models)
- [ ] Implement `src/bevigil_client.py`
- [ ] Implement `src/supabase_client.py`
- [ ] Implement `src/enrichment_service.py`

### Step 4: CLI & Scripts
- [ ] Implement `scripts/run_enrichment.py`
- [ ] Implement `scripts/check_status.py`

### Step 5: Testing & Validation
- [ ] Test with 1 app (dry run)
- [ ] Verify data in Supabase
- [ ] Run full enrichment

---

## Estimated API Credits Required

| Endpoint | Credits/App | Apps | Total |
|----------|-------------|------|-------|
| `/all-assets/` | 1 | 89 | 89 |
| `/report/` | 1 | 89 | 89 |
| **Total** | 2 | 89 | **178 credits** |

---

## Runtime Estimate

- 89 Android apps
- 2 API calls per app = 178 requests
- 1.5 seconds delay between requests
- ~4.5 minutes total runtime (plus processing time)
- Estimate: **~5-7 minutes** for full enrichment

---

## Questions Requiring Answers

### Required Information:

1. **Supabase Service Key**
   - Need the service role key for the arkuts project
   - This allows backend operations (bypasses RLS)
   - Found in: Supabase Dashboard → Settings → API → service_role key

2. **Supabase Project URL**
   - Already have project ID: `ggobqbgvmcufrebeloen`
   - URL format: `https://ggobqbgvmcufrebeloen.supabase.co`
   - Please confirm this is correct

### Optional Clarifications:

3. **Re-enrichment Strategy**
   - Should we ever re-enrich already completed apps?
   - If yes, after how long? (e.g., 30 days)
   - Or only manual trigger?

4. **Failure Handling**
   - For apps marked 'not_found' (not in BeVigil DB):
     - Should we retry these periodically?
     - Or mark as permanently unavailable?

5. **Notification Preferences**
   - Should the script output to console only?
   - Or would you like log files as well?

6. **RLS (Row Level Security)**
   - Should RLS be enabled on the new tables?
   - If yes, what policies are needed?
   - (Recommendation: disable for backend-only tables)

---

## Next Steps After Approval

1. You provide: Supabase service key + confirm project URL
2. I create: Database tables via migration
3. I create: All Python code files
4. I create: Documentation (README)
5. You run: `pip install -r requirements.txt`
6. You create: `.env` file with credentials
7. You run: `python scripts/run_enrichment.py`
8. Verify: Check data in Supabase dashboard

---

## Success Criteria

- [ ] All 89 Android apps attempted
- [ ] Enrichment data stored in `bevigil_enrichment`
- [ ] Vulnerabilities stored in `bevigil_vulnerabilities`
- [ ] Clear status tracking (completed/not_found/failed)
- [ ] No duplicate processing on re-run
- [ ] Queryable vulnerability data with CWE/CVSS
