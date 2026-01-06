# BeVigil Security Analysis Report

## Overview

This document provides a comprehensive overview of our mobile app security intelligence database, powered by BeVigil OSINT (Open Source Intelligence). The system scans Android applications to identify security vulnerabilities, exposed secrets, and configuration issues that could be exploited by malicious actors.

---

## What We're Tracking

We maintain two interconnected databases that store security intelligence for Android applications:

1. **App Enrichment Data** - High-level security scores, asset counts, and metadata for each app
2. **Vulnerability Details** - Individual security findings with severity ratings and remediation guidance

---

## Current Analysis Summary

| Metric | Value |
|--------|-------|
| **Apps Analysed** | 8 |
| **Total Vulnerabilities Found** | 579 |
| **Exposed Secrets Detected** | 5,980 |
| **Manifest Issues** | 148 |
| **Apps with Grade D (Poor)** | 8 (100%) |

### Apps Analysed

| App Name | Category | Security Grade | Security Score | Total Vulnerabilities |
|----------|----------|----------------|----------------|----------------------|
| Textra SMS | Communication | D | 8.10 | 27 |
| Solitaire | Card Game | D | 7.90 | 56 |
| Facebook | Social | D | 7.10 | 127 |
| YouTube | Video | D | 6.83 | 57 |
| Kik Messenger | Communication | D | 6.74 | 101 |
| Instagram | Social | D | 6.72 | 58 |
| WhatsApp | Communication | D | 6.71 | 120 |
| Chomp SMS | Communication | D | 6.50 | 33 |

> **Note:** Security scores range from 0.0 (best) to 10.0 (worst). All analysed apps received a "D" grade, indicating significant security concerns.

---

## Understanding the Data

### Security Grades Explained

| Grade | Score Range | Meaning |
|-------|-------------|---------|
| A | 0.0 - 2.0 | Excellent security posture |
| B | 2.1 - 4.0 | Good security with minor issues |
| C | 4.1 - 6.0 | Moderate security concerns |
| D | 6.1 - 8.0 | Poor security, significant vulnerabilities |
| F | 8.1 - 10.0 | Critical security failures |

### Vulnerability Categories

| Category | Description | Example Issues |
|----------|-------------|----------------|
| **Vulnerabilities (vuln)** | Code-level security weaknesses | Weak encryption, insecure data handling |
| **Secrets** | Exposed credentials and keys | API keys, tokens, passwords in code |
| **Manifest** | Android configuration issues | Exported components, missing permissions |
| **Assets** | Exposed infrastructure information | URLs, IP addresses, cloud storage buckets |

### Severity Levels

| Severity | CVSS Score | Risk Level |
|----------|------------|------------|
| **Critical** | 9.0 - 10.0 | Immediate exploitation risk |
| **High** | 7.0 - 8.9 | Serious security threat |
| **Medium** | 4.0 - 6.9 | Moderate risk, should be addressed |
| **Low** | 0.1 - 3.9 | Minor risk, best practice improvements |
| **Info** | 0.0 | Informational, no direct risk |

---

## Key Findings

### 1. Universal Vulnerabilities (Found in ALL 8 Apps)

These issues were discovered in every single application analysed:

| Vulnerability | Category | Risk | Occurrences |
|--------------|----------|------|-------------|
| Hardcoded Secrets | Secrets | Medium | 5,635 instances |
| Insecure Random Numbers | Code | High | 830 instances |
| Exported Activities | Manifest | Medium | 119 instances |
| Object Deserialization | Code | Critical | 89 instances |
| Google API Keys Exposed | Secrets | Medium | 48 instances |
| CBC Padding Oracle | Crypto | Critical | 47 instances |

### 2. High-Risk Vulnerabilities by App

| App | Critical Finding | Instances | CVSS Score |
|-----|-----------------|-----------|------------|
| Facebook | Insecure Random Number Generation | 261 | 10.0 |
| Instagram | Insecure Random Number Generation | 166 | 10.0 |
| WhatsApp | CBC Padding Oracle Attack | 19 | 10.0 |
| Facebook | Object Deserialization | 23 | 10.0 |
| WhatsApp | Object Deserialization | 18 | 10.0 |

### 3. Exposed Secrets Summary

| App | High-Entropy Strings | Possible Secrets | API Keys |
|-----|---------------------|------------------|----------|
| Facebook | 2,001 | 44 | 3 |
| Instagram | 2,001 | 30 | 2 |
| Kik | 877 | 29 | 5 |
| WhatsApp | 393 | 24 | 3 |
| YouTube | 255 | 9 | 30 |

### 4. Privacy Concerns - Trackers

| App | Third-Party Libraries | Trackers Detected |
|-----|----------------------|-------------------|
| Solitaire | 60 | 17 |
| Kik | 112 | 16 |
| Textra SMS | 42 | 8 |
| Facebook | 62 | 8 |
| Chomp SMS | 39 | 7 |
| Instagram | 68 | 4 |
| YouTube | 47 | 2 |
| WhatsApp | 60 | 1 |

---

## How Attackers Could Exploit These Vulnerabilities

### Insecure Random Number Generation (CVSS 10.0)
**Found in:** All 8 apps (830 total instances)

**What it means:** The app uses predictable methods to generate "random" numbers for security-sensitive operations.

**Attack scenario:** An attacker could:
- Predict session tokens and hijack user accounts
- Guess password reset codes
- Decrypt communications that rely on these "random" values
- Forge authentication tokens

**Real-world impact:** Account takeover, identity theft, unauthorised access to private messages and data.

---

### Object Deserialization (CWE-502, CVSS 10.0)
**Found in:** All 8 apps (89 total instances)

**What it means:** The app converts data from external sources into internal objects without proper validation.

**Attack scenario:** An attacker could:
- Craft malicious data that executes code when the app processes it
- Gain remote code execution on the victim's device
- Install malware or spyware without user knowledge
- Access all data stored by the application

**Real-world impact:** Complete device compromise, data theft, surveillance capabilities.

---

### CBC Padding Oracle Attack (CVSS 10.0)
**Found in:** 8 apps (47 total instances)

**What it means:** A flaw in how encryption is implemented allows attackers to decrypt protected data.

**Attack scenario:** An attacker could:
- Intercept encrypted communications between the app and servers
- Decrypt private messages, passwords, and financial data
- Modify encrypted data without detection
- Bypass authentication mechanisms

**Real-world impact:** Exposure of private conversations, financial fraud, privacy breaches.

---

### Exported Activities/Services (CWE-926)
**Found in:** All 8 apps (148 total instances)

**What it means:** App components are accessible to other apps on the device without proper protection.

**Attack scenario:** An attacker's malicious app could:
- Launch hidden screens in the target app
- Bypass login screens and access protected features
- Trigger actions the user didn't authorise
- Extract data through unprotected interfaces

**Real-world impact:** Bypassed security controls, unauthorised actions, data leakage.

---

### Hardcoded Secrets (CWE-798)
**Found in:** All 8 apps (5,979 total instances)

**What it means:** API keys, tokens, and credentials are embedded directly in the app code.

**Attack scenario:** An attacker could:
- Extract API keys to access backend services
- Impersonate the app to access user data
- Exhaust API quotas causing service disruption
- Access cloud storage, databases, or third-party services

**Real-world impact:** Data breaches, service abuse, financial losses from API misuse.

---

### SQL Injection Potential (CWE-89)
**Found in:** 5 apps (47 total instances)

**What it means:** Database queries are constructed using user input without proper sanitisation.

**Attack scenario:** An attacker could:
- Extract entire databases of user information
- Modify or delete user data
- Bypass authentication
- Escalate privileges within the app

**Real-world impact:** Mass data breaches, account manipulation, service disruption.

---

### WebView Security Issues (CWE-749, CWE-919)
**Found in:** 6 apps (35 total instances)

**What it means:** In-app browsers have dangerous features enabled or ignore security warnings.

**Attack scenario:** An attacker could:
- Inject malicious JavaScript into web content
- Steal session cookies and authentication tokens
- Redirect users to phishing sites
- Execute code in the context of the app

**Real-world impact:** Credential theft, phishing attacks, malware distribution.

---

## Data Dictionary

### Table: bevigil_enrichment

The main enrichment table containing high-level security analysis for each app.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique identifier for the enrichment record |
| `app_id` | Integer | Foreign key linking to the apps table |
| `bundle_id` | String | Android package name (e.g., com.facebook.katana) |
| `enrichment_status` | String | Processing status: pending, processing, completed, failed, not_found, no_credits |
| `severity_grade` | String | Overall security grade: A (best) to F (worst) |
| `severity_score` | Decimal | Numeric security score: 0.0 (best) to 10.0 (worst) |
| `vuln_total` | Integer | Total code vulnerabilities found |
| `vuln_high` | Integer | High severity vulnerability count |
| `vuln_medium` | Integer | Medium severity vulnerability count |
| `vuln_low` | Integer | Low severity vulnerability count |
| `secrets_total` | Integer | Total exposed secrets/credentials found |
| `secrets_high` | Integer | High severity secret exposures |
| `secrets_medium` | Integer | Medium severity secret exposures |
| `secrets_low` | Integer | Low severity secret exposures |
| `manifest_total` | Integer | Total Android manifest configuration issues |
| `assets_total` | Integer | Total exposed assets (URLs, IPs, etc.) |
| `host_count` | Integer | Number of unique hostnames found in app |
| `url_count` | Integer | Number of URLs found in app |
| `s3_bucket_count` | Integer | Number of Amazon S3 bucket references |
| `firebase_url_count` | Integer | Number of Firebase database URLs |
| `email_count` | Integer | Number of email addresses found |
| `ip_address_count` | Integer | Number of IP addresses found |
| `third_party_lib_count` | Integer | Number of third-party libraries used |
| `tracker_count` | Integer | Number of tracking/analytics SDKs detected |
| `hosts` | Array | List of hostnames found |
| `urls` | Array | List of URLs found |
| `s3_buckets` | Array | List of S3 bucket URLs |
| `firebase_urls` | Array | List of Firebase URLs |
| `emails` | Array | List of email addresses |
| `trackers` | Array | List of tracking SDKs detected |
| `third_party_libs` | Array | List of third-party libraries |
| `created_at` | Timestamp | When the record was created |
| `updated_at` | Timestamp | When the record was last updated |
| `last_enriched_at` | Timestamp | When the app was last scanned |

### Table: bevigil_vulnerabilities

Individual vulnerability findings with detailed information.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique identifier for the vulnerability |
| `enrichment_id` | Integer | Foreign key to bevigil_enrichment |
| `app_id` | Integer | Foreign key to apps table |
| `vuln_type` | String | Specific vulnerability type identifier |
| `category` | String | Category: vuln, secrets, manifest, or assets |
| `cwe_id` | String | Common Weakness Enumeration ID (industry standard) |
| `cwe_name` | String | Human-readable CWE name |
| `severity` | String | Risk level: critical, high, medium, low, info |
| `cvss_score` | Decimal | Common Vulnerability Scoring System score (0.0-10.0) |
| `description` | Text | Detailed explanation of the vulnerability |
| `mitigation` | Text | Recommended fix or remediation steps |
| `reference` | Text | Links to additional resources |
| `match_count` | Integer | Number of times this issue was found in the app |
| `sample_matches` | JSON | Example code/locations where issue was found |
| `affected_files` | Array | List of files containing the vulnerability |
| `created_at` | Timestamp | When the vulnerability was recorded |

---

## CWE Reference Guide

Common Weakness Enumeration (CWE) IDs found in our analysis:

| CWE ID | Name | Apps Affected | Description |
|--------|------|---------------|-------------|
| CWE-798 | Hardcoded Credentials | 8 | Credentials stored directly in source code |
| CWE-926 | Improper Export of Android Components | 8 | App components accessible to other apps |
| CWE-327 | Weak Cryptographic Algorithm | 8 | Use of broken or risky cryptographic algorithms |
| CWE-502 | Deserialization of Untrusted Data | 8 | Processing external data without validation |
| CWE-295 | Improper Certificate Validation | 6 | Accepting invalid SSL/TLS certificates |
| CWE-749 | Exposed Dangerous Method | 6 | WebView JavaScript enabled without safeguards |
| CWE-89 | SQL Injection | 5 | Database queries vulnerable to manipulation |
| CWE-532 | Information in Log Files | 5 | Sensitive data written to logs |
| CWE-919 | Weaknesses in Mobile Applications | 4 | WebView debugging enabled in production |
| CWE-312 | Cleartext Storage of Sensitive Info | 3 | Sensitive data stored without encryption |
| CWE-757 | Selection of Less-Secure Algorithm | 2 | Choosing weak algorithms when stronger available |

---

## Recommendations

### For Security Teams

1. **Prioritise Critical Vulnerabilities** - Focus first on CVSS 10.0 issues: insecure random numbers, deserialization flaws, and padding oracle attacks

2. **Audit Exported Components** - Review all 148 exported activities/services to ensure they require appropriate permissions

3. **Rotate Exposed Credentials** - Any API keys or secrets found in the app code should be considered compromised and rotated immediately

4. **Review Third-Party Libraries** - Apps with high library counts (Kik: 112, Instagram: 68) have larger attack surfaces

### For Developers

1. Use `SecureRandom` instead of `java.util.Random` for security-sensitive operations
2. Implement proper input validation before deserializing objects
3. Use GCM mode instead of CBC for encryption
4. Store secrets in secure keystores, not in code
5. Mark components as `exported="false"` unless external access is required

---

## Data Source

This analysis is powered by **BeVigil OSINT API** by CloudSEK, which maintains a database of over 500,000 Android applications. The data represents static analysis of the app packages and does not include runtime or network analysis.

**Limitations:**
- Only Android apps are supported (no iOS analysis)
- Analysis is point-in-time; apps may have been updated since scanning
- Some findings may be false positives requiring manual verification
- Severity scores are automated assessments, not manual penetration testing

---

*Report generated: January 2026*
*Data source: BeVigil OSINT API*
*Analysis scope: 8 Android applications*
