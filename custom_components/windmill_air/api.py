"""Async client for the Windmill (Blynk) device HTTPS API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from .const import BASE_URL, LOGGER

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class WindmillApiError(Exception):
    """Raised when the Windmill cloud API returns an error."""


class WindmillAuthError(WindmillApiError):
    """Raised when the device token is rejected."""


class WindmillAirApi:
    """Minimal client for Blynk's device HTTPS API on dashboard.windmillair.com.

    Endpoints (token-authenticated, one token per device):
      GET /external/api/getAll?token=X                -> {"v0": 1, "v1": 3, ...}
      GET /external/api/get?token=X&v0                -> value
      GET /external/api/update?token=X&v0=1           -> 200 on success
      GET /external/api/isHardwareConnected?token=X   -> "true" / "false"
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self._token = token
        self._base_url = base_url.rstrip("/")

    async def _request(self, endpoint: str, params: dict[str, Any]) -> str:
        url = f"{self._base_url}/external/api/{endpoint}"
        query = {"token": self._token, **params}
        try:
            async with self._session.get(
                url, params=query, timeout=REQUEST_TIMEOUT
            ) as resp:
                body = await resp.text()
                if resp.status in (400, 401, 403) and "token" in body.lower():
                    raise WindmillAuthError(f"Token rejected: {body}")
                if resp.status != 200:
                    raise WindmillApiError(
                        f"{endpoint} returned HTTP {resp.status}: {body}"
                    )
                return body
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise WindmillApiError(f"Error calling {endpoint}: {err}") from err

    async def get_all(self) -> dict[str, Any]:
        """Return all datastream values, keys normalized to lowercase (v0, v1...)."""
        body = await self._request("getAll", {})
        try:
            data = json.loads(body)
        except ValueError as err:
            raise WindmillApiError(f"Unexpected getAll response: {body!r}") from err
        if not isinstance(data, dict):
            raise WindmillApiError(f"Unexpected getAll response: {body!r}")
        return {str(k).lower(): v for k, v in data.items()}

    async def get_pin(self, pin: str) -> str:
        """Return the raw value of a single datastream."""
        return (await self._request("get", {pin.lower(): ""})).strip('[]" \n')

    async def set_pin(self, pin: str, value: Any) -> None:
        """Write a value to a datastream."""
        LOGGER.debug("Setting %s to %s", pin, value)
        await self._request("update", {pin.lower(): value})

    async def is_connected(self) -> bool:
        """Return True if the device is online (also validates the token)."""
        body = await self._request("isHardwareConnected", {})
        return body.strip().lower() == "true"
