"""Tests for the Idle Clans API client.

These tests use ``unittest.mock`` to patch ``requests.Session.get`` so that
no real network calls are made.  Each test verifies that:
  - The client builds the correct URL / params.
  - The response JSON is correctly parsed into model objects.
  - HTTP errors are translated into the appropriate custom exceptions.
"""

from __future__ import annotations

import json
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
import requests
from idle_clans_tools.api.client import IdleClansClient
from idle_clans_tools.api.exceptions import (
    IdleClansAPIError,
    NetworkError,
    NotFoundError,
    RateLimitError,
)
from idle_clans_tools.api.models import (
    ClanInfo,
    ClanMember,
    LeaderboardEntry,
    MarketItem,
    PlayerProfile,
)

# ---------------------------------------------------------------------------
# Helper to build a fake requests.Response
# ---------------------------------------------------------------------------


def _make_response(status_code: int, body: object) -> MagicMock:
    """Create a mock :class:`requests.Response` with the given status and JSON body."""
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = body
    response.text = json.dumps(body)
    return response


def _session_get_mock(client: IdleClansClient) -> MagicMock:
    """Return the mocked ``Session.get`` with the correct static type for tests."""
    session = cast(Any, client._session)
    return cast(MagicMock, session.get)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> IdleClansClient:
    """Return an IdleClansClient backed by a fresh mock session."""
    mock_session = MagicMock(spec=requests.Session)
    mock_session.headers = {}
    return IdleClansClient(session=mock_session)


# ---------------------------------------------------------------------------
# Player tests
# ---------------------------------------------------------------------------


class TestGetPlayerProfile:
    def test_returns_player_profile(self, client: IdleClansClient) -> None:
        payload = {
            "username": "HeroPlayer",
            "guildName": "BraveClan",
            "combatLevel": 50,
            "skillExperiences": {"woodcutting": 100_000, "mining": 200_000},
        }
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        profile = client.get_player_profile("HeroPlayer")

        assert isinstance(profile, PlayerProfile)
        assert profile.username == "HeroPlayer"
        assert profile.clan_name == "BraveClan"
        assert profile.total_experience == 300_000
        assert profile.combat_level == 50
        assert profile.skills["woodcutting"] == 100_000

    def test_calls_correct_url_with_encoding(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, {"username": "x"})
        client.get_player_profile("Test User")

        call_args = get_mock.call_args
        assert "/api/Player/profile/Test%20User" in call_args[0][0]

    def test_raises_not_found(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(404, {"error": "not found"})
        with pytest.raises(NotFoundError):
            client.get_player_profile("Nobody")

    def test_raises_rate_limit(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(429, {})
        with pytest.raises(RateLimitError):
            client.get_player_profile("SpamUser")

    def test_raises_api_error_on_5xx(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(500, {"error": "server error"})
        with pytest.raises(IdleClansAPIError):
            client.get_player_profile("ServerError")

    def test_raises_network_error_on_timeout(self, client: IdleClansClient) -> None:
        from requests.exceptions import Timeout

        get_mock = _session_get_mock(client)
        get_mock.side_effect = Timeout()
        with pytest.raises(NetworkError):
            client.get_player_profile("TimeoutUser")

    def test_raises_network_error_on_connection_error(self, client: IdleClansClient) -> None:
        from requests.exceptions import ConnectionError as CE

        get_mock = _session_get_mock(client)
        get_mock.side_effect = CE()
        with pytest.raises(NetworkError):
            client.get_player_profile("OfflineUser")


# ---------------------------------------------------------------------------
# Clan tests
# ---------------------------------------------------------------------------


class TestGetClanInfo:
    def test_returns_clan_info(self, client: IdleClansClient) -> None:
        payload = {
            "clanName": "BraveClan",
            "tag": "BC",
            "memberCount": 12,
            "isRecruiting": True,
            "language": "English",
            "category": "PvE",
            "recruitmentMessage": "We are brave.",
        }
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        info = client.get_clan_info("BraveClan")

        assert isinstance(info, ClanInfo)
        assert info.name == "BraveClan"
        assert info.tag == "BC"
        assert info.member_count == 12
        assert info.is_recruiting is True
        assert info.language == "English"
        assert info.description == "We are brave."

    def test_encodes_clan_name_in_url(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, {"clanName": "Brave Clan"})

        client.get_clan_info("Brave Clan")

        call_args = get_mock.call_args
        assert "/api/Clan/recruitment/Brave%20Clan" in call_args[0][0]

    def test_raises_not_found_for_missing_clan(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(404, {})
        with pytest.raises(NotFoundError):
            client.get_clan_info("NonExistentClan")


class TestGetClanMembers:
    def test_returns_member_list_from_recruitment_memberlist(self, client: IdleClansClient) -> None:
        payload = {
            "memberlist": [
                {"memberName": "Alice", "rank": 3},
                {"memberName": "Bob", "rank": 1},
            ]
        }
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        members = client.get_clan_members("BraveClan")

        assert len(members) == 2
        assert all(isinstance(m, ClanMember) for m in members)
        assert members[0].username == "Alice"
        assert members[1].rank == "1"

    def test_returns_empty_members_when_payload_not_dict(self, client: IdleClansClient) -> None:
        payload = []
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        members = client.get_clan_members("BraveClan")
        assert members == []


# ---------------------------------------------------------------------------
# Leaderboard tests
# ---------------------------------------------------------------------------


class TestGetLeaderboard:
    def test_returns_leaderboard_entries(self, client: IdleClansClient) -> None:
        payload = [
            {"rank": 1, "username": "Top", "value": 999_999},
            {"rank": 2, "username": "Second", "value": 888_888},
        ]
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        entries = client.get_leaderboard("total_level")

        assert len(entries) == 2
        assert all(isinstance(e, LeaderboardEntry) for e in entries)
        assert entries[0].rank == 1
        assert entries[0].username == "Top"

    def test_passes_page_params(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, [])
        client.get_leaderboard("mining", page=3, page_size=5)

        call_url = get_mock.call_args[0][0]
        call_kwargs = get_mock.call_args[1]
        assert "/api/Leaderboard/top/players%3Adefault/mining" in call_url
        assert call_kwargs["params"]["startCount"] == 11
        assert call_kwargs["params"]["maxCount"] == 5

    def test_handles_wrapped_response(self, client: IdleClansClient) -> None:
        payload = {"entries": [{"rank": 1, "name": "Ace", "fields": {"xp": 123}}]}
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        entries = client.get_leaderboard("total_level")
        assert len(entries) == 1
        assert entries[0].username == "Ace"
        assert entries[0].value == 123


# ---------------------------------------------------------------------------
# Market tests
# ---------------------------------------------------------------------------


class TestGetMarketItems:
    def test_returns_market_items(self, client: IdleClansClient) -> None:
        payload = [
            {
                "itemId": 1,
                "itemName": "Iron Ore",
                "lowestPrice": 50,
                "volume": 100,
            }
        ]
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        items = client.get_market_items()

        assert len(items) == 1
        assert isinstance(items[0], MarketItem)
        assert items[0].item_name == "Iron Ore"
        assert items[0].price == 50
        assert items[0].quantity == 100

    def test_passes_market_price_query_param(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, [])
        client.get_market_items(item_name="Coal")

        call_kwargs = get_mock.call_args[1]
        assert call_kwargs["params"]["includeAveragePrice"] is True

    def test_filters_market_items_client_side(self, client: IdleClansClient) -> None:
        payload = [
            {"itemId": 1, "itemName": "Coal", "lowestPrice": 25},
            {"itemId": 2, "itemName": "Iron Ore", "lowestPrice": 50},
        ]
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        items = client.get_market_items(item_name="coal")

        assert len(items) == 1
        assert items[0].item_name == "Coal"

    def test_handles_map_response(self, client: IdleClansClient) -> None:
        payload = {
            "Iron Ore": {"itemId": 2, "lowestPrice": 500, "volume": 10},
            "Coal": {"itemId": 3, "lowestPrice": 20, "volume": 200},
        }
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        items = client.get_market_items()

        assert len(items) == 2
        assert any(i.item_name == "Iron Ore" for i in items)


# ---------------------------------------------------------------------------
# _get helper tests
# ---------------------------------------------------------------------------


class TestGetHelper:
    def test_raises_api_error_on_non_json_success(self, client: IdleClansClient) -> None:
        get_mock = _session_get_mock(client)
        response = _make_response(200, {})
        response.json.side_effect = ValueError("bad json")
        get_mock.return_value = response

        with pytest.raises(IdleClansAPIError):
            client.get_player_profile("BadJson")

    def test_raises_network_error_on_generic_request_exception(
        self, client: IdleClansClient
    ) -> None:
        from requests.exceptions import RequestException

        get_mock = _session_get_mock(client)
        get_mock.side_effect = RequestException()

        with pytest.raises(NetworkError):
            client.get_player_profile("GenericFailure")

        call_kwargs = get_mock.call_args[1]
        assert call_kwargs["params"] is None

    def test_handles_wrapped_response(self, client: IdleClansClient) -> None:
        payload = {
            "items": [
                {
                    "itemId": 2,
                    "itemName": "Gold Bar",
                    "price": 500,
                    "quantity": 10,
                    "seller": None,
                }
            ]
        }
        get_mock = _session_get_mock(client)
        get_mock.return_value = _make_response(200, payload)

        items = client.get_market_items()
        assert items[0].item_name == "Gold Bar"
        assert items[0].seller is None


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_player_profile_defaults(self) -> None:
        profile = PlayerProfile.from_dict({})
        assert profile.username == ""
        assert profile.clan_name is None
        assert profile.total_experience == 0
        assert profile.skills == {}

    def test_clan_info_defaults(self) -> None:
        info = ClanInfo.from_dict({})
        assert info.leader == ""
        assert info.description is None
        assert info.is_recruiting is None

    def test_leaderboard_entry_defaults(self) -> None:
        entry = LeaderboardEntry.from_dict({})
        assert entry.rank == 0
        assert entry.value == 0

    def test_market_item_defaults(self) -> None:
        item = MarketItem.from_dict({})
        assert item.item_id == 0
        assert item.seller is None

    def test_market_item_supports_latest_price_shape(self) -> None:
        item = MarketItem.from_dict({"itemName": "Coal", "lowestPrice": 123, "volume": 77})
        assert item.item_name == "Coal"
        assert item.price == 123
        assert item.quantity == 77
