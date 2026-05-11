"""Supabase database client for BeVigil enrichment."""

from typing import Optional
from datetime import datetime

from supabase import create_client, Client

from .config import config
from .models import App, EnrichmentRecord, VulnerabilityRecord, EnrichmentStats


class SupabaseClient:
    """Client for Supabase database operations."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ):
        """Initialize the Supabase client."""
        self.url = url or config.SUPABASE_URL
        self.key = key or config.SUPABASE_SECRET_KEY

        if not self.url or not self.key:
            raise ValueError("Supabase URL and SUPABASE_SECRET_KEY are required")

        self._client: Client = create_client(self.url, self.key)

    def get_pending_apps(
        self,
        limit: Optional[int] = None,
        category: Optional[str] = None,
        app_name_contains: Optional[str] = None,
        bundle_id_contains: Optional[str] = None,
        developer_contains: Optional[str] = None,
        include_failed: bool = False,
    ) -> list[App]:
        """
        Get Android apps that need enrichment.

        Args:
            limit: Maximum number of apps to return
            category: Filter by app category
            app_name_contains: Filter by app name (case-insensitive contains)
            bundle_id_contains: Filter by bundle ID (case-insensitive contains)
            developer_contains: Filter by developer name (case-insensitive contains)
            include_failed: Include previously failed apps for retry

        Returns:
            List of App objects pending enrichment
        """
        # Build the query for Android apps
        query = (
            self._client.table("apps")
            .select("id, bundle_id, platform, app_name, developer_name, category, version, metadata")
            .eq("platform", "Android")
        )

        # Apply filters
        if category:
            query = query.eq("category", category)
        if app_name_contains:
            query = query.ilike("app_name", f"%{app_name_contains}%")
        if bundle_id_contains:
            query = query.ilike("bundle_id", f"%{bundle_id_contains}%")
        if developer_contains:
            query = query.ilike("developer_name", f"%{developer_contains}%")

        # Get all matching apps
        result = query.execute()
        all_apps = [App(**row) for row in result.data]

        # Get apps that already have enrichment
        enrichment_query = self._client.table("bevigil_enrichment").select(
            "app_id, enrichment_status"
        )
        enrichment_result = enrichment_query.execute()

        # Build set of app_ids to exclude
        exclude_statuses = {"completed", "not_found", "no_credits"}
        if not include_failed:
            exclude_statuses.add("failed")

        enriched_app_ids = {
            row["app_id"]
            for row in enrichment_result.data
            if row["enrichment_status"] in exclude_statuses
        }

        # Filter out already enriched apps
        pending_apps = [app for app in all_apps if app.id not in enriched_app_ids]

        # Apply limit
        if limit:
            pending_apps = pending_apps[:limit]

        return pending_apps

    def get_enrichment_by_app_id(self, app_id: int) -> Optional[dict]:
        """Get existing enrichment record for an app."""
        result = (
            self._client.table("bevigil_enrichment")
            .select("*")
            .eq("app_id", app_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def upsert_enrichment(self, record: EnrichmentRecord) -> int:
        """
        Insert or update an enrichment record.

        Returns:
            The enrichment record ID
        """
        data = record.model_dump(exclude_none=True)

        # Convert datetime objects to ISO strings
        for key in ["last_enriched_at", "cert_valid_from", "cert_valid_to"]:
            if key in data and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()

        result = (
            self._client.table("bevigil_enrichment")
            .upsert(data, on_conflict="app_id")
            .execute()
        )

        return result.data[0]["id"]

    def insert_vulnerabilities(self, vulnerabilities: list[VulnerabilityRecord]) -> None:
        """Insert vulnerability records (batch insert)."""
        if not vulnerabilities:
            return

        data = []
        for vuln in vulnerabilities:
            vuln_data = vuln.model_dump(exclude_none=True)
            data.append(vuln_data)

        # Use upsert to handle potential duplicates
        self._client.table("bevigil_vulnerabilities").upsert(
            data, on_conflict="enrichment_id,vuln_type,category"
        ).execute()

    def delete_vulnerabilities_for_enrichment(self, enrichment_id: int) -> None:
        """Delete all vulnerabilities for an enrichment record (for re-processing)."""
        self._client.table("bevigil_vulnerabilities").delete().eq(
            "enrichment_id", enrichment_id
        ).execute()

    def update_status(
        self,
        app_id: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the enrichment status for an app."""
        data = {"enrichment_status": status}
        if error_message:
            data["error_message"] = error_message

        self._client.table("bevigil_enrichment").update(data).eq(
            "app_id", app_id
        ).execute()

    def increment_retry_count(self, app_id: int) -> None:
        """Increment the retry count for an app."""
        # Get current count
        result = (
            self._client.table("bevigil_enrichment")
            .select("retry_count")
            .eq("app_id", app_id)
            .execute()
        )

        if result.data:
            current_count = result.data[0].get("retry_count", 0) or 0
            self._client.table("bevigil_enrichment").update(
                {"retry_count": current_count + 1}
            ).eq("app_id", app_id).execute()

    def get_stats(self) -> EnrichmentStats:
        """Get enrichment statistics."""
        # Total Android apps
        android_result = (
            self._client.table("apps")
            .select("id", count="exact")
            .eq("platform", "Android")
            .execute()
        )

        # Enrichment status counts
        enrichment_result = (
            self._client.table("bevigil_enrichment")
            .select("enrichment_status")
            .execute()
        )

        status_counts = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "not_found": 0,
            "no_credits": 0,
        }

        for row in enrichment_result.data:
            status = row.get("enrichment_status", "pending")
            if status in status_counts:
                status_counts[status] += 1

        return EnrichmentStats(
            total_android_apps=android_result.count or 0,
            **status_counts,
        )

    def get_android_app_categories(self) -> list[str]:
        """Get list of unique categories for Android apps."""
        result = (
            self._client.table("apps")
            .select("category")
            .eq("platform", "Android")
            .not_.is_("category", "null")
            .execute()
        )

        categories = set()
        for row in result.data:
            if row.get("category"):
                categories.add(row["category"])

        return sorted(categories)

    def get_android_app_developers(self) -> list[str]:
        """Get list of unique developers for Android apps."""
        result = (
            self._client.table("apps")
            .select("developer_name")
            .eq("platform", "Android")
            .not_.is_("developer_name", "null")
            .execute()
        )

        developers = set()
        for row in result.data:
            if row.get("developer_name"):
                developers.add(row["developer_name"])

        return sorted(developers)

    def get_app_by_bundle_id(self, bundle_id: str) -> Optional[App]:
        """Get an app by its bundle ID."""
        result = (
            self._client.table("apps")
            .select("id, bundle_id, platform, app_name, developer_name, category, version, release_date, metadata")
            .eq("bundle_id", bundle_id)
            .execute()
        )
        if result.data:
            return App(**result.data[0])
        return None

    def create_app(
        self,
        bundle_id: str,
        platform: str = "Android",
        app_name: Optional[str] = None,
        developer_name: Optional[str] = None,
        category: Optional[str] = None,
        version: Optional[str] = None,
        release_date: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> App:
        """Create a new app record and return it."""
        data = {"bundle_id": bundle_id, "platform": platform}
        if app_name:
            data["app_name"] = app_name
        if developer_name:
            data["developer_name"] = developer_name
        if category:
            data["category"] = category
        if version:
            data["version"] = version
        if release_date:
            data["release_date"] = release_date
        if metadata:
            data["metadata"] = metadata
        result = (
            self._client.table("apps")
            .insert(data)
            .execute()
        )
        return App(**result.data[0])

    def update_app_metadata(
        self,
        app_id: int,
        app_name: Optional[str] = None,
        developer_name: Optional[str] = None,
        category: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Update app metadata fields (only updates fields that are provided)."""
        data = {}
        if app_name:
            data["app_name"] = app_name
        if developer_name:
            data["developer_name"] = developer_name
        if category:
            data["category"] = category
        if version:
            data["version"] = version
        if metadata:
            data["metadata"] = metadata
        
        if data:
            self._client.table("apps").update(data).eq("id", app_id).execute()

    def get_or_create_app(
        self,
        bundle_id: str,
        platform: str = "Android",
        app_name: Optional[str] = None,
        developer_name: Optional[str] = None,
        category: Optional[str] = None,
        version: Optional[str] = None,
        release_date: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> App:
        """Get an existing app or create a new one. Updates missing metadata if app exists."""
        app = self.get_app_by_bundle_id(bundle_id)
        if app:
            # Only update fields that are provided AND currently missing
            updates = {}
            if app_name and not app.app_name:
                updates["app_name"] = app_name
            if developer_name and not app.developer_name:
                updates["developer_name"] = developer_name
            if category and not app.category:
                updates["category"] = category
            if version and not app.version:
                updates["version"] = version
            if release_date and not app.release_date:
                updates["release_date"] = release_date
            if metadata and not app.metadata:
                updates["metadata"] = metadata
            
            if updates:
                self._client.table("apps").update(updates).eq("id", app.id).execute()
                # Update local object
                for key, value in updates.items():
                    setattr(app, key, value)
            return app
        return self.create_app(bundle_id, platform, app_name, developer_name, category, version, release_date, metadata)
