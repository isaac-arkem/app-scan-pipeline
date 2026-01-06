# BeVigil App Enrichment

Enrich Android app data with security intelligence from the [BeVigil OSINT API](https://bevigil.com/osint-api).

## Overview

This tool fetches security and asset data for Android apps from BeVigil's mobile security intelligence platform and stores it in Supabase. It extracts:

- **Security vulnerabilities** with CWE IDs, CVSS scores, and severity ratings
- **Exposed assets**: hosts, URLs, S3 buckets, Firebase URLs, emails, IPs
- **Third-party libraries** and trackers
- **Certificate information**
- **Overall security grade** (A-F)

## Installation

```bash
# Clone or navigate to the repository
cd App_Enrichment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

Create a `.env` file with:

```env
BEVIGIL_API_KEY=your_bevigil_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

Optional settings:
```env
BATCH_SIZE=10          # Apps per batch
REQUEST_DELAY=1.5      # Seconds between API calls
MAX_RETRIES=3          # Retry attempts on failure
```

## Usage

### Check Current Status

```bash
python scripts/check_status.py

# Detailed stats with vulnerability breakdown
python scripts/check_status.py --detailed
```

### Run Enrichment

```bash
# Show help and all options
python scripts/run_enrichment.py --help

# Process a limited number of apps (recommended for testing)
python scripts/run_enrichment.py --limit 5

# Dry run - see what would be processed without making API calls
python scripts/run_enrichment.py --dry-run --limit 20

# Filter by category
python scripts/run_enrichment.py --category Games --limit 10

# Filter by developer
python scripts/run_enrichment.py --developer "Google" --limit 10

# Filter by app name
python scripts/run_enrichment.py --app-name "Facebook" --limit 5

# Filter by bundle ID
python scripts/run_enrichment.py --bundle-id "com.google" --limit 10

# Retry previously failed apps
python scripts/run_enrichment.py --include-failed --limit 10

# List available categories
python scripts/run_enrichment.py --list-categories

# List available developers
python scripts/run_enrichment.py --list-developers
```

### Combining Filters

```bash
# Games by a specific developer, limit 5
python scripts/run_enrichment.py --category Games --developer "Zynga" --limit 5

# All social apps, dry run first
python scripts/run_enrichment.py --category Social --dry-run
```

## CLI Options Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--limit` | `-l` | Maximum number of apps to process |
| `--category` | `-c` | Filter by app category |
| `--app-name` | `-a` | Filter by app name (contains) |
| `--bundle-id` | `-b` | Filter by bundle ID (contains) |
| `--developer` | `-d` | Filter by developer name (contains) |
| `--include-failed` | `-f` | Include previously failed apps |
| `--dry-run` | | Preview without API calls |
| `--list-categories` | | Show available categories |
| `--list-developers` | | Show available developers |

## Database Schema

### `bevigil_enrichment`
Main enrichment data table with:
- Security scores and grades
- Vulnerability counts by severity
- Extracted assets (hosts, URLs, S3 buckets, emails, etc.)
- Certificate information
- Raw API responses

### `bevigil_vulnerabilities`
Normalized vulnerability findings with:
- CWE IDs and names
- CVSS scores
- Severity levels
- Descriptions and mitigations
- Affected files

## API Credit Usage

Each app requires **2 API calls**:
1. `/all-assets/` - Asset extraction
2. `/report/` - Security report

**Example**: Processing 89 apps = 178 API credits

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| `completed` | Successfully enriched | ✓ Done |
| `not_found` | App not in BeVigil DB | Skipped permanently |
| `failed` | Processing error | Can retry with `--include-failed` |
| `no_credits` | API credits exhausted | Stop processing |

## Example Queries

### High-Risk Apps
```sql
SELECT a.app_name, be.severity_grade, be.vuln_high
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE be.vuln_high > 0
ORDER BY be.severity_score DESC;
```

### Vulnerabilities by CWE
```sql
SELECT cwe_id, cwe_name, COUNT(*) as count
FROM bevigil_vulnerabilities
WHERE cwe_id IS NOT NULL
GROUP BY cwe_id, cwe_name
ORDER BY count DESC;
```

### Apps with Exposed S3 Buckets
```sql
SELECT a.app_name, be.s3_buckets
FROM apps a
JOIN bevigil_enrichment be ON a.id = be.app_id
WHERE be.s3_bucket_count > 0;
```

## Project Structure

```
App_Enrichment/
├── src/
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic data models
│   ├── bevigil_client.py      # BeVigil API client
│   ├── supabase_client.py     # Database operations
│   └── enrichment_service.py  # Main enrichment logic
├── scripts/
│   ├── run_enrichment.py      # CLI for enrichment
│   └── check_status.py        # CLI for status
├── requirements.txt
├── .env.example
└── README.md
```

## License

Internal use only.
