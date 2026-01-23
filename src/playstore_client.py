"""Google Play Store client for fetching app metadata."""

from typing import Optional
from dataclasses import dataclass

from google_play_scraper import app as get_app_info
from google_play_scraper.exceptions import NotFoundError


@dataclass
class AppMetadata:
    """App metadata from Google Play Store."""
    
    app_name: Optional[str] = None
    developer_name: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    rating: Optional[float] = None
    installs: Optional[str] = None
    released: Optional[str] = None  # Release date string
    updated: Optional[str] = None   # Last updated date


class PlayStoreClient:
    """Client for fetching app metadata from Google Play Store."""

    def get_app_metadata(self, bundle_id: str) -> Optional[AppMetadata]:
        """
        Fetch app metadata from Google Play Store.
        
        Args:
            bundle_id: The Android package name (e.g., com.whatsapp)
            
        Returns:
            AppMetadata if found, None if app not found
        """
        try:
            result = get_app_info(bundle_id, lang='en', country='us')
            
            return AppMetadata(
                app_name=result.get('title'),
                developer_name=result.get('developer'),
                category=result.get('genre'),
                version=result.get('version'),
                description=result.get('description'),
                icon_url=result.get('icon'),
                rating=result.get('score'),
                installs=result.get('installs'),
                released=result.get('released'),
                updated=result.get('updated'),
            )
        except NotFoundError:
            return None
        except Exception:
            # Silently handle other errors (rate limiting, network issues, etc.)
            return None
