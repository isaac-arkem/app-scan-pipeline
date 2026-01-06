"""BeVigil API client with rate limiting and error handling."""

import time
from typing import Optional, Any
from enum import Enum

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .config import config


class BeVigilError(Exception):
    """Base exception for BeVigil API errors."""

    pass


class RateLimitError(BeVigilError):
    """Rate limit exceeded."""

    pass


class NoCreditsError(BeVigilError):
    """No API credits remaining."""

    pass


class NotFoundError(BeVigilError):
    """App not found in BeVigil database."""

    pass


class AuthenticationError(BeVigilError):
    """Invalid API key."""

    pass


class ApiStatus(Enum):
    """API response status."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    NO_CREDITS = "no_credits"
    ERROR = "error"


class BeVigilClient:
    """Client for BeVigil OSINT API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the BeVigil client."""
        self.api_key = api_key or config.BEVIGIL_API_KEY
        self.base_url = config.BEVIGIL_BASE_URL
        self.timeout = config.REQUEST_TIMEOUT
        self.request_delay = config.REQUEST_DELAY
        self._last_request_time: float = 0

        if not self.api_key:
            raise ValueError("BeVigil API key is required")

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-Access-Token": self.api_key},
            timeout=self.timeout,
        )

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise NotFoundError(f"App not found in BeVigil database")
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 402:
            raise NoCreditsError("No API credits remaining")
        elif response.status_code == 422:
            raise RateLimitError("Rate limit exceeded")
        else:
            raise BeVigilError(
                f"API error: {response.status_code} - {response.text}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    def _request(self, endpoint: str) -> dict[str, Any]:
        """Make a rate-limited request to the API."""
        self._rate_limit()
        response = self._client.get(endpoint)
        return self._handle_response(response)

    def get_all_assets(self, package_id: str) -> tuple[ApiStatus, Optional[dict]]:
        """
        Get all assets for a package.

        Returns:
            Tuple of (status, data)
        """
        try:
            data = self._request(f"/api/{package_id}/all-assets/")
            return ApiStatus.SUCCESS, data
        except NotFoundError:
            return ApiStatus.NOT_FOUND, None
        except NoCreditsError:
            return ApiStatus.NO_CREDITS, None
        except RateLimitError:
            return ApiStatus.RATE_LIMITED, None
        except Exception as e:
            return ApiStatus.ERROR, {"error": str(e)}

    def get_report(self, package_id: str) -> tuple[ApiStatus, Optional[dict]]:
        """
        Get security report for a package.

        Returns:
            Tuple of (status, data)
        """
        try:
            data = self._request(f"/api/{package_id}/report/")
            return ApiStatus.SUCCESS, data
        except NotFoundError:
            return ApiStatus.NOT_FOUND, None
        except NoCreditsError:
            return ApiStatus.NO_CREDITS, None
        except RateLimitError:
            return ApiStatus.RATE_LIMITED, None
        except Exception as e:
            return ApiStatus.ERROR, {"error": str(e)}

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "BeVigilClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
