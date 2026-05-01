"""HTTP client for the Idle Clans public API.

Usage::

    from idle_clans_tools.api import IdleClansClient

    client = IdleClansClient()
    player = client.get_player_profile("some_player")
    print(player.username, player.total_experience)

The client handles:
- JSON parsing
- HTTP error codes (404, 429, 5xx)
- Network failures (timeouts, connection errors)
- Rate-limit feedback (HTTP 429)
"""

from __future__ import annotations

from typing import Any

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

from .exceptions import IdleClansAPIError, NetworkError, NotFoundError, RateLimitError
from .models import (
    ClanInfo,
    ClanMember,
    LeaderboardEntry,
    MarketItem,
    PlayerProfile,
)

# Base URL for the public Idle Clans query API
_BASE_URL = "https://query.idleclans.com"

# Default request timeout in seconds (connect, read)
_DEFAULT_TIMEOUT = (5, 15)


class IdleClansClient:
    """A thin wrapper around the Idle Clans public REST API.

    Args:
        base_url: Override the API base URL (useful for testing).
        timeout: ``(connect_timeout, read_timeout)`` in seconds.
        session: Provide a custom :class:`requests.Session` (useful for
            mocking in tests).
    """

    def __init__(
        self,
        base_url: str = _BASE_URL,
        timeout: tuple[int, int] = _DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a GET request and return the parsed JSON payload.

        Raises:
            NotFoundError: HTTP 404.
            RateLimitError: HTTP 429.
            IdleClansAPIError: Any other non-2xx HTTP response.
            NetworkError: Connection or timeout failure.
        """
        url = f"{self.base_url}{path}"
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
        except Timeout as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except RequestsConnectionError as exc:
            raise NetworkError(f"Connection failed: {url}") from exc

        if response.status_code == 404:
            raise NotFoundError(
                f"Resource not found: {url}", status_code=404
            )
        if response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded. Please slow down requests.",
                status_code=429,
            )
        if not response.ok:
            raise IdleClansAPIError(
                f"API returned status {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        return response.json()

    # ------------------------------------------------------------------
    # Player endpoints
    # ------------------------------------------------------------------

    def get_player_profile(self, username: str) -> PlayerProfile:
        """Fetch a player's profile by username.

        Args:
            username: The in-game player username.

        Returns:
            A :class:`~idle_clans_tools.api.models.PlayerProfile` instance.
        """
        data = self._get(f"/api/Player/profile/{username}")
        return PlayerProfile.from_dict(data)

    # ------------------------------------------------------------------
    # Clan endpoints
    # ------------------------------------------------------------------

    def get_clan_info(self, clan_name: str) -> ClanInfo:
        """Fetch basic information about a clan.

        Args:
            clan_name: The exact clan name as it appears in-game.

        Returns:
            A :class:`~idle_clans_tools.api.models.ClanInfo` instance.
        """
        data = self._get(f"/api/Clan/info/{clan_name}")
        return ClanInfo.from_dict(data)

    def get_clan_members(self, clan_name: str) -> list[ClanMember]:
        """Fetch the member list for a clan.

        Args:
            clan_name: The exact clan name as it appears in-game.

        Returns:
            A list of :class:`~idle_clans_tools.api.models.ClanMember` objects.
        """
        data = self._get(f"/api/Clan/members/{clan_name}")
        if not isinstance(data, list):
            data = data.get("members", [])
        return [ClanMember.from_dict(entry) for entry in data]

    # ------------------------------------------------------------------
    # Leaderboard endpoints
    # ------------------------------------------------------------------

    def get_leaderboard(
        self, category: str, page: int = 1, page_size: int = 25
    ) -> list[LeaderboardEntry]:
        """Fetch a leaderboard for the given category.

        Common categories include ``total``, ``combat``, ``woodcutting``,
        ``mining``, ``fishing``, etc.

        Args:
            category: The skill or total leaderboard category name.
            page: Page number (1-indexed).
            page_size: Number of entries per page.

        Returns:
            A list of :class:`~idle_clans_tools.api.models.LeaderboardEntry`
            objects sorted by rank.
        """
        data = self._get(
            f"/api/Leaderboards/{category}",
            params={"page": page, "pageSize": page_size},
        )
        if not isinstance(data, list):
            data = data.get("entries", [])
        return [LeaderboardEntry.from_dict(entry) for entry in data]

    # ------------------------------------------------------------------
    # Market endpoints
    # ------------------------------------------------------------------

    def get_market_items(self, item_name: str | None = None) -> list[MarketItem]:
        """Fetch current player market listings.

        Args:
            item_name: Optional filter — return only listings for this item
                name.

        Returns:
            A list of :class:`~idle_clans_tools.api.models.MarketItem` objects.
        """
        params: dict[str, Any] = {}
        if item_name:
            params["itemName"] = item_name

        data = self._get("/api/PlayerMarket/items", params=params or None)
        if not isinstance(data, list):
            data = data.get("items", [])
        return [MarketItem.from_dict(entry) for entry in data]
