"""Data models for BeVigil App Enrichment."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class App(BaseModel):
    """App record from Supabase apps table."""

    id: int
    bundle_id: str
    platform: str
    app_name: Optional[str] = None
    developer_name: Optional[str] = None
    category: Optional[str] = None


class EnrichmentRecord(BaseModel):
    """Enrichment record for database."""

    app_id: int
    bundle_id: str
    enrichment_status: str = "pending"
    error_message: Optional[str] = None
    retry_count: int = 0
    last_enriched_at: Optional[datetime] = None

    # Security Rating
    severity_grade: Optional[str] = None
    severity_score: Optional[float] = None

    # Issue Counts
    vuln_total: int = 0
    vuln_high: int = 0
    vuln_medium: int = 0
    vuln_low: int = 0

    secrets_total: int = 0
    secrets_high: int = 0
    secrets_medium: int = 0
    secrets_low: int = 0

    assets_total: int = 0

    manifest_total: int = 0
    manifest_high: int = 0
    manifest_medium: int = 0
    manifest_low: int = 0

    # Asset Counts
    host_count: int = 0
    url_count: int = 0
    s3_bucket_count: int = 0
    firebase_url_count: int = 0
    email_count: int = 0
    ip_address_count: int = 0
    rest_api_count: int = 0
    file_path_count: int = 0

    # Metadata Counts
    third_party_lib_count: int = 0
    tracker_count: int = 0

    # Certificate Info
    apk_signed: Optional[bool] = None
    v1_signature: Optional[bool] = None
    v2_signature: Optional[bool] = None
    v3_signature: Optional[bool] = None
    cert_issuer: Optional[str] = None
    cert_subject: Optional[str] = None
    cert_valid_from: Optional[datetime] = None
    cert_valid_to: Optional[datetime] = None
    cert_sha256: Optional[str] = None

    # Extracted Arrays
    hosts: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    s3_buckets: list[str] = Field(default_factory=list)
    firebase_urls: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    ip_addresses: list[str] = Field(default_factory=list)
    rest_apis: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)
    third_party_libs: list[str] = Field(default_factory=list)
    trackers: list[str] = Field(default_factory=list)

    # Raw Responses
    all_assets_response: Optional[dict] = None
    report_response: Optional[dict] = None


class VulnerabilityRecord(BaseModel):
    """Vulnerability record for database."""

    enrichment_id: int
    app_id: int
    vuln_type: str
    category: str  # vuln, secrets, manifest, assets
    cwe_id: Optional[str] = None
    cwe_name: Optional[str] = None
    severity: str  # critical, high, medium, low, info
    cvss_score: Optional[float] = None
    description: Optional[str] = None
    mitigation: Optional[str] = None
    reference: Optional[str] = None
    match_count: int = 1
    sample_matches: Optional[list[dict]] = None
    affected_files: list[str] = Field(default_factory=list)


class BeVigilAssetsResponse(BaseModel):
    """Response from BeVigil /all-assets/ endpoint."""

    package_id: str
    host: dict[str, Any] = Field(default_factory=dict)


class BeVigilReportResponse(BaseModel):
    """Response from BeVigil /report/ endpoint."""

    package_id: str
    report: Optional[dict[str, Any]] = None


class EnrichmentStats(BaseModel):
    """Statistics for enrichment progress."""

    total_android_apps: int = 0
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    not_found: int = 0
    no_credits: int = 0
