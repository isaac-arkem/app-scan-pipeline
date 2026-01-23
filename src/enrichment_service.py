"""Main enrichment service orchestrating BeVigil API calls and database updates."""

from datetime import datetime, timezone
from typing import Optional, Any, Callable

from .models import App, EnrichmentRecord, VulnerabilityRecord
from .bevigil_client import BeVigilClient, ApiStatus
from .supabase_client import SupabaseClient


class EnrichmentService:
    """Service for enriching app data with BeVigil intelligence."""

    def __init__(
        self,
        bevigil_client: Optional[BeVigilClient] = None,
        supabase_client: Optional[SupabaseClient] = None,
    ):
        """Initialize the enrichment service."""
        self._bevigil = bevigil_client or BeVigilClient()
        self._supabase = supabase_client or SupabaseClient()

    def enrich_app(
        self,
        app: App,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> tuple[bool, str]:
        """
        Enrich a single app with BeVigil data.

        Args:
            app: The app to enrich
            on_progress: Optional callback for progress updates

        Returns:
            Tuple of (success, status_message)
        """
        bundle_id = app.bundle_id

        def log(msg: str) -> None:
            if on_progress:
                on_progress(msg)

        # Create initial enrichment record with processing status
        initial_record = EnrichmentRecord(
            app_id=app.id,
            bundle_id=bundle_id,
            enrichment_status="processing",
        )

        try:
            # Check if record exists
            existing = self._supabase.get_enrichment_by_app_id(app.id)
            if existing:
                enrichment_id = existing["id"]
                self._supabase.update_status(app.id, "processing")
                # Clear old vulnerabilities for re-processing
                self._supabase.delete_vulnerabilities_for_enrichment(enrichment_id)
            else:
                enrichment_id = self._supabase.upsert_enrichment(initial_record)

        except Exception as e:
            return False, f"Database error: {str(e)}"

        # Fetch all-assets data
        log(f"Fetching assets for {bundle_id}...")
        assets_status, assets_data = self._bevigil.get_all_assets(bundle_id)

        if assets_status == ApiStatus.NO_CREDITS:
            self._supabase.update_status(app.id, "no_credits", "API credits exhausted")
            return False, "no_credits"

        if assets_status == ApiStatus.NOT_FOUND:
            self._supabase.update_status(app.id, "not_found", "App not in BeVigil database")
            return True, "not_found"

        if assets_status == ApiStatus.RATE_LIMITED:
            self._supabase.update_status(app.id, "failed", "Rate limit exceeded after retries")
            self._supabase.increment_retry_count(app.id)
            return False, "rate_limited"

        if assets_status == ApiStatus.ERROR:
            error_msg = assets_data.get("error", "Unknown error") if assets_data else "Unknown error"
            self._supabase.update_status(app.id, "failed", error_msg)
            self._supabase.increment_retry_count(app.id)
            return False, f"error: {error_msg}"

        # Fetch report data
        log(f"Fetching security report for {bundle_id}...")
        report_status, report_data = self._bevigil.get_report(bundle_id)

        if report_status == ApiStatus.NO_CREDITS:
            self._supabase.update_status(app.id, "no_credits", "API credits exhausted")
            return False, "no_credits"

        # Process and store the data
        try:
            log(f"Processing data for {bundle_id}...")
            enrichment_record = self._build_enrichment_record(
                app=app,
                assets_data=assets_data,
                report_data=report_data if report_status == ApiStatus.SUCCESS else None,
            )
            enrichment_record.last_enriched_at = datetime.now(timezone.utc)

            # Check if we got meaningful data
            has_assets = (
                enrichment_record.host_count > 0 or
                enrichment_record.url_count > 0 or
                enrichment_record.s3_bucket_count > 0 or
                enrichment_record.firebase_url_count > 0 or
                enrichment_record.email_count > 0 or
                enrichment_record.ip_address_count > 0
            )
            has_report = (
                enrichment_record.severity_grade is not None or
                enrichment_record.vuln_total > 0 or
                enrichment_record.secrets_total > 0 or
                enrichment_record.manifest_total > 0
            )

            if has_assets or has_report:
                enrichment_record.enrichment_status = "completed"
                final_status = "completed"
            else:
                enrichment_record.enrichment_status = "not_found"
                final_status = "not_found"
                log(f"Warning: BeVigil returned no meaningful data for {bundle_id}")

            # Upsert the enrichment record
            enrichment_id = self._supabase.upsert_enrichment(enrichment_record)

            # Extract and insert vulnerabilities
            if report_status == ApiStatus.SUCCESS and report_data:
                vulnerabilities = self._extract_vulnerabilities(
                    enrichment_id=enrichment_id,
                    app_id=app.id,
                    report_data=report_data,
                )
                if vulnerabilities:
                    log(f"Inserting {len(vulnerabilities)} vulnerability records...")
                    self._supabase.insert_vulnerabilities(vulnerabilities)

            return True, final_status

        except Exception as e:
            self._supabase.update_status(app.id, "failed", str(e))
            self._supabase.increment_retry_count(app.id)
            return False, f"processing_error: {str(e)}"

    def _build_enrichment_record(
        self,
        app: App,
        assets_data: Optional[dict],
        report_data: Optional[dict],
    ) -> EnrichmentRecord:
        """Build an enrichment record from API responses."""
        record = EnrichmentRecord(
            app_id=app.id,
            bundle_id=app.bundle_id,
            all_assets_response=assets_data,
            report_response=report_data,
        )

        # Extract assets
        if assets_data:
            host_data = assets_data.get("host") or {}

            record.hosts = self._extract_list(host_data, "host")
            record.urls = self._extract_list(host_data, "url")
            record.s3_buckets = self._extract_list(host_data, "AWS URL")
            record.firebase_urls = self._extract_list(host_data, "Firebase URL")
            record.emails = self._extract_list(host_data, "email")
            record.ip_addresses = self._extract_list(host_data, "IP Address disclosure")
            record.rest_apis = self._extract_list(host_data, "rest_api")
            record.file_paths = self._extract_list(host_data, "file_path")

            record.host_count = len(record.hosts)
            record.url_count = len(record.urls)
            record.s3_bucket_count = len(record.s3_buckets)
            record.firebase_url_count = len(record.firebase_urls)
            record.email_count = len(record.emails)
            record.ip_address_count = len(record.ip_addresses)
            record.rest_api_count = len(record.rest_apis)
            record.file_path_count = len(record.file_paths)

        # Extract report data
        if report_data:
            report = report_data.get("report") or {}

            # Severity rating
            severity_rating = report.get("severity_rating") or {}
            record.severity_grade = severity_rating.get("severity_grade")
            record.security_score = severity_rating.get("severity_score")

            # Issue counts
            report_summary = report.get("report_summary") or {}
            issues_per_scanner = report_summary.get("issues_per_scanner_counts") or {}

            vuln_counts = issues_per_scanner.get("vuln") or {}
            record.vuln_total = vuln_counts.get("total", 0) or 0
            record.vuln_high = vuln_counts.get("high", 0) or 0
            record.vuln_medium = vuln_counts.get("medium", 0) or 0
            record.vuln_low = vuln_counts.get("low", 0) or 0

            secrets_counts = issues_per_scanner.get("secrets") or {}
            record.secrets_total = secrets_counts.get("total", 0) or 0
            record.secrets_high = secrets_counts.get("high", 0) or 0
            record.secrets_medium = secrets_counts.get("medium", 0) or 0
            record.secrets_low = secrets_counts.get("low", 0) or 0

            assets_counts = issues_per_scanner.get("assets") or {}
            record.assets_total = assets_counts.get("total", 0) or 0

            manifest_counts = issues_per_scanner.get("manifest") or {}
            record.manifest_total = manifest_counts.get("total", 0) or 0
            record.manifest_high = manifest_counts.get("high", 0) or 0
            record.manifest_medium = manifest_counts.get("medium", 0) or 0
            record.manifest_low = manifest_counts.get("low", 0) or 0

            # Metadata
            results_metadata = report.get("results_metadata") or {}

            third_party_libs = results_metadata.get("third_party_libs") or []
            record.third_party_libs = [lib.get("name", "") for lib in third_party_libs if isinstance(lib, dict) and lib.get("name")]
            record.third_party_lib_count = len(record.third_party_libs)

            trackers = results_metadata.get("trackers") or []
            record.trackers = [t.get("name", "") for t in trackers if isinstance(t, dict) and t.get("name")]
            record.tracker_count = len(record.trackers)

            # Certificate info
            cert_data = results_metadata.get("certificate") or {}
            cert_info = cert_data.get("certificate_info") or {}

            record.apk_signed = cert_info.get("apk_signed")
            record.v1_signature = cert_info.get("v1_signature")
            record.v2_signature = cert_info.get("v2_signature")
            record.v3_signature = cert_info.get("v3_signature")

            cert_list = cert_info.get("cert_list") or []
            if cert_list and isinstance(cert_list[0], dict):
                cert = cert_list[0]
                record.cert_issuer = cert.get("Issuer")
                record.cert_subject = cert.get("Subject")
                record.cert_sha256 = cert.get("sha256")

                # Parse dates
                valid_from = cert.get("Valid From")
                valid_to = cert.get("Valid To")
                if valid_from:
                    try:
                        record.cert_valid_from = datetime.fromisoformat(
                            valid_from.replace("+00:00", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass
                if valid_to:
                    try:
                        record.cert_valid_to = datetime.fromisoformat(
                            valid_to.replace("+00:00", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

        return record

    def _extract_list(self, data: dict, key: str) -> list[str]:
        """Extract a list of strings from nested data."""
        value = data.get(key, [])
        if isinstance(value, list):
            return [str(v) for v in value if v]
        return []

    def _extract_vulnerabilities(
        self,
        enrichment_id: int,
        app_id: int,
        report_data: dict,
    ) -> list[VulnerabilityRecord]:
        """Extract vulnerability records from report data."""
        vulnerabilities = []
        report = report_data.get("report") or {}
        results_issues = report.get("results_issues") or {}

        # Process each category
        categories = [
            ("vuln", "vuln"),
            ("secrets", "secrets"),
            ("manifest", "manifest"),
        ]

        for category_key, category_name in categories:
            issues = results_issues.get(category_key) or []

            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                vuln_type = issue.get("type", "unknown") or "unknown"
                issue_info = issue.get("issue_info") or {}
                matches = issue.get("matches") or []

                # Map severity
                severity_raw = issue_info.get("severity") or "info"
                severity = self._normalize_severity(severity_raw)

                # Extract affected files
                affected_files = []
                for match in matches[:10]:  # Limit to 10 files
                    if isinstance(match, dict):
                        filename = match.get("filename")
                        if filename:
                            affected_files.append(filename)

                # Sample matches (first 5)
                sample_matches = matches[:5] if matches else None

                vuln = VulnerabilityRecord(
                    enrichment_id=enrichment_id,
                    app_id=app_id,
                    vuln_type=vuln_type,
                    category=category_name,
                    cwe_id=issue_info.get("cwe_id"),
                    cwe_name=issue_info.get("cwe_name"),
                    severity=severity,
                    cvss_score=issue_info.get("cvss_score"),
                    description=issue_info.get("description"),
                    mitigation=issue_info.get("mitigation"),
                    reference=issue_info.get("reference"),
                    match_count=len(matches),
                    sample_matches=sample_matches,
                    affected_files=affected_files,
                )

                vulnerabilities.append(vuln)

        return vulnerabilities

    def _normalize_severity(self, severity: str) -> str:
        """Normalize severity string to valid enum value."""
        if not severity:
            return "info"
        severity_lower = severity.lower()
        if severity_lower in ("critical", "high", "medium", "low", "info"):
            return severity_lower
        # Map common variations
        if severity_lower in ("severe", "important"):
            return "high"
        if severity_lower in ("moderate", "warning"):
            return "medium"
        if severity_lower in ("informational", "information", "none"):
            return "info"
        return "info"

    def close(self) -> None:
        """Close underlying clients."""
        self._bevigil.close()
