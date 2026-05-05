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

import json
import re
from typing import Any
from urllib.parse import quote

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .exceptions import IdleClansAPIError, NetworkError, NotFoundError, RateLimitError
from .models import (
    ClanCupStanding,
    ClanExperienceSummary,
    ClanInfo,
    ClanMember,
    GameItem,
    LeaderboardEntry,
    MarketItem,
    PlayerActivity,
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
        self._item_lookup_cache: dict[int, GameItem] | None = None
        self._clan_upgrade_lookup_cache: dict[int, str] | None = None

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
        except RequestException as exc:
            raise NetworkError(f"Request failed: {url}") from exc

        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {url}", status_code=404)
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

        try:
            return response.json()
        except ValueError as exc:
            raise IdleClansAPIError(
                "API returned a non-JSON response.", status_code=response.status_code
            ) from exc

    def _get_game_data(self) -> dict[str, Any]:
        """Fetch game-data, normalizing Mongo-style ObjectId tokens."""
        url = f"{self.base_url}/api/Configuration/game-data"
        try:
            response = self._session.get(url, params=None, timeout=self.timeout)
        except Timeout as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except RequestsConnectionError as exc:
            raise NetworkError(f"Connection failed: {url}") from exc
        except RequestException as exc:
            raise NetworkError(f"Request failed: {url}") from exc

        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {url}", status_code=404)
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

        raw_payload = response.text
        try:
            for _ in range(2):
                normalized = re.sub(
                    r'ObjectId\("([^"]+)"\)',
                    lambda match: json.dumps(match.group(1)),
                    raw_payload,
                )
                data = json.loads(normalized)
                if not isinstance(data, str):
                    break
                raw_payload = data
        except ValueError as exc:
            raise IdleClansAPIError(
                "Game-data endpoint returned an unsupported response.",
                status_code=response.status_code,
            ) from exc

        if not isinstance(data, dict):
            raise IdleClansAPIError(
                "Game-data endpoint returned an unexpected payload.",
                status_code=response.status_code,
            )
        return data

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
        safe_username = quote(username, safe="")
        data = self._get(f"/api/Player/profile/{safe_username}")
        return PlayerProfile.from_dict(data)

    def get_player_activities(self, usernames: list[str]) -> dict[str, PlayerActivity]:
        """Fetch the current activity for a batch of players.

        Args:
            usernames: List of player usernames to query.  The API accepts up
                to ~100 usernames per request.

        Returns:
            A ``dict`` mapping each username to its
            :class:`~idle_clans_tools.api.models.PlayerActivity`.
        """
        if not usernames:
            return {}
        params = [("usernames", u) for u in usernames]
        data = self._get("/api/Player/activities", params=params)
        if not isinstance(data, dict):
            return {}
        return {
            str(name): PlayerActivity.from_dict(activity)
            for name, activity in data.items()
            if isinstance(activity, dict)
        }

    def get_player_simple_profiles(self, usernames: list[str]) -> dict[str, PlayerProfile]:
        """Fetch simple profiles for a batch of players.

        The simple profile payload contains the same fields used by
        idle-clans-hub for activity indicators (for example
        ``taskTypeOnLogout`` and ``taskNameOnLogout``).
        """
        profiles: dict[str, PlayerProfile] = {}
        for username in usernames:
            safe_username = quote(username, safe="")
            try:
                data = self._get(f"/api/Player/profile/simple/{safe_username}")
            except NotFoundError:
                continue
            if not isinstance(data, dict):
                continue
            profiles[username] = PlayerProfile.from_dict(data)
        return profiles

    def get_player_activity_details(
        self,
        activities: dict[str, PlayerActivity],
    ) -> dict[str, str]:
        """Resolve a readable task name for each player's activity.

        This follows the same source used by idle-clans-hub:
        ``/api/Player/profile/simple/{username}`` -> ``taskNameOnLogout``.
        """
        if not activities:
            return {}

        profiles = self.get_player_simple_profiles(list(activities))
        details: dict[str, str] = {}

        for username, profile in profiles.items():
            task_name = profile.task_name_on_logout
            if isinstance(task_name, str) and task_name.strip():
                details[username] = task_name.strip()

        return details

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
        safe_clan_name = quote(clan_name, safe="")
        data = self._get(f"/api/Clan/recruitment/{safe_clan_name}")
        return ClanInfo.from_dict(data)

    def get_clan_members(self, clan_name: str) -> list[ClanMember]:
        """Fetch the member list for a clan.

        Args:
            clan_name: The exact clan name as it appears in-game.

        Returns:
            A list of :class:`~idle_clans_tools.api.models.ClanMember` objects.
        """
        safe_clan_name = quote(clan_name, safe="")
        data = self._get(f"/api/Clan/recruitment/{safe_clan_name}")
        if not isinstance(data, dict):
            return []
        data = data.get("memberlist", [])
        return [ClanMember.from_dict(entry) for entry in data]

    def get_clan_cup_standings(
        self,
        clan_name: str,
        game_mode: str = "Default",
        previous_cup: bool = False,
    ) -> list[ClanCupStanding]:
        """Fetch a clan's standings for all Clan Cup objectives.

        Args:
            clan_name: The exact clan name as it appears in-game.
            game_mode: Game mode to retrieve standings for (e.g. ``"Default"``,
                ``"Ironman"``). Defaults to ``"Default"``.
            previous_cup: If ``True``, return standings for the previous cup.

        Returns:
            A list of :class:`~idle_clans_tools.api.models.ClanCupStanding`
            objects, one per objective category.
        """
        safe_clan_name = quote(clan_name, safe="")
        params: dict[str, Any] = {"gameMode": game_mode, "previousCup": previous_cup}
        data = self._get(f"/api/ClanCup/standings/{safe_clan_name}", params=params)
        if not isinstance(data, list):
            return []
        return [ClanCupStanding.from_dict(entry) for entry in data if isinstance(entry, dict)]

    def get_clan_experience_summary(
        self,
        clan_name: str,
        hours: int = 72,
    ) -> ClanExperienceSummary:
        """Fetch experience totals and player contributions for a clan.

        Args:
            clan_name: The exact clan name as it appears in-game.
            hours: Number of hours to look back. Supported range is 1-168.

        Returns:
            A :class:`~idle_clans_tools.api.models.ClanExperienceSummary` instance.
        """
        safe_clan_name = quote(clan_name, safe="")
        data = self._get(f"/api/Clan/{safe_clan_name}/experience", params={"hours": hours})
        if not isinstance(data, dict):
            data = {}
        return ClanExperienceSummary.from_dict(data)

    # ------------------------------------------------------------------
    # Leaderboard endpoints
    # ------------------------------------------------------------------

    def get_leaderboard(
        self,
        category: str,
        page: int = 1,
        page_size: int = 25,
        leaderboard_name: str = "players:default",
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
        start_count = max(1, ((page - 1) * page_size) + 1)
        safe_leaderboard_name = quote(leaderboard_name, safe="")
        safe_category = quote(category, safe="")
        data = self._get(
            f"/api/Leaderboard/top/{safe_leaderboard_name}/{safe_category}",
            params={"startCount": start_count, "maxCount": page_size},
        )
        if isinstance(data, dict):
            # Some deployments wrap list payloads under an "entries" key.
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
        data = self._get(
            "/api/PlayerMarket/items/prices/latest",
            params={"includeAveragePrice": True},
        )

        # The market endpoint can return either a list or a map keyed by item id/name.
        entries: list[dict[str, Any]] = []
        if isinstance(data, list):
            entries = [entry for entry in data if isinstance(entry, dict)]
        elif isinstance(data, dict):
            raw_items = data.get("items") if isinstance(data.get("items"), list) else None
            if raw_items is not None:
                entries = [entry for entry in raw_items if isinstance(entry, dict)]
            else:
                for key, value in data.items():
                    if isinstance(value, dict):
                        hydrated = dict(value)
                        if "itemName" not in hydrated and isinstance(key, str):
                            hydrated["itemName"] = key
                        entries.append(hydrated)

        items = [MarketItem.from_dict(entry) for entry in entries]
        if not item_name:
            return items

        needle = item_name.casefold()
        return [item for item in items if needle in item.item_name.casefold()]

    # ------------------------------------------------------------------
    # Configuration endpoints
    # ------------------------------------------------------------------

    def get_game_items(self) -> list[GameItem]:
        """Fetch static item metadata from the game-data endpoint."""
        data = self._get_game_data()
        items_payload = data.get("Items")
        if isinstance(items_payload, dict):
            items_payload = items_payload.get("Items", [])
        if not isinstance(items_payload, list):
            return []
        return [GameItem.from_dict(entry) for entry in items_payload if isinstance(entry, dict)]

    def get_item_lookup(self) -> dict[int, GameItem]:
        """Fetch static item metadata keyed by item id."""
        if self._item_lookup_cache is None:
            self._item_lookup_cache = {item.item_id: item for item in self.get_game_items()}
        return dict(self._item_lookup_cache)

    def get_clan_upgrade_lookup(self) -> dict[int, str]:
        """Fetch clan upgrade definitions keyed by upgrade type id.

        Returns:
            A dict mapping upgrade ``Type`` integer to a human-readable name.
        """
        if self._clan_upgrade_lookup_cache is not None:
            return dict(self._clan_upgrade_lookup_cache)
        data = self._get_game_data()
        raw = data.get("ClanUpgrades", {})
        if isinstance(raw, dict):
            items = raw.get("Items", [])
        elif isinstance(raw, list):
            items = raw
        else:
            items = []
        lookup: dict[int, str] = {}
        for entry in items:
            if not isinstance(entry, dict):
                continue
            type_id = entry.get("Type")
            if not isinstance(type_id, int):
                continue
            loc_keys = entry.get("TierDescriptionLocKeys") or []
            loc_key = loc_keys[0] if loc_keys else ""
            name = (
                loc_key.replace("clan_upgrade_", "")
                .removesuffix("_description")
                .removesuffix("_desc")
                .replace("_", " ")
                .title()
            )
            lookup[type_id] = name or f"Upgrade {type_id}"
        self._clan_upgrade_lookup_cache = lookup
        return dict(lookup)
