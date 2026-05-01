"""Tests for the Idle Clans API client.

These tests use ``unittest.mock`` to patch ``requests.Session.get`` so that
no real network calls are made.  Each test verifies that:
  - The client builds the correct URL / params.
  - The response JSON is correctly parsed into model objects.
  - HTTP errors are translated into the appropriate custom exceptions.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

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
            "clanName": "BraveClan",
            "totalExperience": 1_000_000,
            "combatLevel": 50,
            "skills": {"woodcutting": 100_000, "mining": 200_000},
        }
        client._session.get.return_value = _make_response(200, payload)

        profile = client.get_player_profile("HeroPlayer")

        assert isinstance(profile, PlayerProfile)
        assert profile.username == "HeroPlayer"
        assert profile.clan_name == "BraveClan"
        assert profile.total_experience == 1_000_000
        assert profile.combat_level == 50
        assert profile.skills["woodcutting"] == 100_000

    def test_calls_correct_url(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(200, {"username": "x"})
        client.get_player_profile("TestUser")

        call_args = client._session.get.call_args
        assert "/api/Player/profile/TestUser" in call_args[0][0]

    def test_raises_not_found(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(404, {"error": "not found"})
        with pytest.raises(NotFoundError):
            client.get_player_profile("Nobody")

    def test_raises_rate_limit(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(429, {})
        with pytest.raises(RateLimitError):
            client.get_player_profile("SpamUser")

    def test_raises_api_error_on_5xx(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(500, {"error": "server error"})
        with pytest.raises(IdleClansAPIError):
            client.get_player_profile("ServerError")

    def test_raises_network_error_on_timeout(self, client: IdleClansClient) -> None:
        from requests.exceptions import Timeout
        client._session.get.side_effect = Timeout()
        with pytest.raises(NetworkError):
            client.get_player_profile("TimeoutUser")

    def test_raises_network_error_on_connection_error(
        self, client: IdleClansClient
    ) -> None:
        from requests.exceptions import ConnectionError as CE
        client._session.get.side_effect = CE()
        with pytest.raises(NetworkError):
            client.get_player_profile("OfflineUser")


# ---------------------------------------------------------------------------
# Clan tests
# ---------------------------------------------------------------------------


class TestGetClanInfo:
    def test_returns_clan_info(self, client: IdleClansClient) -> None:
        payload = {
            "name": "BraveClan",
            "leader": "DragonSlayer",
            "memberCount": 12,
            "totalExperience": 5_000_000,
            "description": "We are brave.",
        }
        client._session.get.return_value = _make_response(200, payload)

        info = client.get_clan_info("BraveClan")

        assert isinstance(info, ClanInfo)
        assert info.name == "BraveClan"
        assert info.leader == "DragonSlayer"
        assert info.member_count == 12
        assert info.description == "We are brave."

    def test_raises_not_found_for_missing_clan(
        self, client: IdleClansClient
    ) -> None:
        client._session.get.return_value = _make_response(404, {})
        with pytest.raises(NotFoundError):
            client.get_clan_info("NonExistentClan")


class TestGetClanMembers:
    def test_returns_member_list_from_array(self, client: IdleClansClient) -> None:
        payload = [
            {"username": "Alice", "rank": "Leader", "totalExperience": 500_000},
            {"username": "Bob", "rank": "Member", "totalExperience": 200_000},
        ]
        client._session.get.return_value = _make_response(200, payload)

        members = client.get_clan_members("BraveClan")

        assert len(members) == 2
        assert all(isinstance(m, ClanMember) for m in members)
        assert members[0].username == "Alice"
        assert members[1].rank == "Member"

    def test_returns_member_list_from_dict(self, client: IdleClansClient) -> None:
        payload = {
            "members": [
                {"username": "Carol", "rank": "Officer", "totalExperience": 300_000},
            ]
        }
        client._session.get.return_value = _make_response(200, payload)

        members = client.get_clan_members("BraveClan")
        assert len(members) == 1
        assert members[0].username == "Carol"


# ---------------------------------------------------------------------------
# Leaderboard tests
# ---------------------------------------------------------------------------


class TestGetLeaderboard:
    def test_returns_leaderboard_entries(self, client: IdleClansClient) -> None:
        payload = [
            {"rank": 1, "username": "Top", "value": 999_999},
            {"rank": 2, "username": "Second", "value": 888_888},
        ]
        client._session.get.return_value = _make_response(200, payload)

        entries = client.get_leaderboard("total")

        assert len(entries) == 2
        assert all(isinstance(e, LeaderboardEntry) for e in entries)
        assert entries[0].rank == 1
        assert entries[0].username == "Top"

    def test_passes_page_params(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(200, [])
        client.get_leaderboard("mining", page=3, page_size=5)

        call_kwargs = client._session.get.call_args[1]
        assert call_kwargs["params"]["page"] == 3
        assert call_kwargs["params"]["pageSize"] == 5

    def test_handles_wrapped_response(self, client: IdleClansClient) -> None:
        payload = {
            "entries": [{"rank": 1, "username": "Ace", "value": 123}]
        }
        client._session.get.return_value = _make_response(200, payload)

        entries = client.get_leaderboard("total")
        assert len(entries) == 1
        assert entries[0].username == "Ace"


# ---------------------------------------------------------------------------
# Market tests
# ---------------------------------------------------------------------------


class TestGetMarketItems:
    def test_returns_market_items(self, client: IdleClansClient) -> None:
        payload = [
            {
                "itemId": 1,
                "itemName": "Iron Ore",
                "price": 50,
                "quantity": 100,
                "seller": "Merchant",
            }
        ]
        client._session.get.return_value = _make_response(200, payload)

        items = client.get_market_items()

        assert len(items) == 1
        assert isinstance(items[0], MarketItem)
        assert items[0].item_name == "Iron Ore"
        assert items[0].price == 50

    def test_passes_item_name_filter(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(200, [])
        client.get_market_items(item_name="Coal")

        call_kwargs = client._session.get.call_args[1]
        assert call_kwargs["params"]["itemName"] == "Coal"

    def test_no_params_when_no_filter(self, client: IdleClansClient) -> None:
        client._session.get.return_value = _make_response(200, [])
        client.get_market_items()

        call_kwargs = client._session.get.call_args[1]
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
        client._session.get.return_value = _make_response(200, payload)

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

    def test_leaderboard_entry_defaults(self) -> None:
        entry = LeaderboardEntry.from_dict({})
        assert entry.rank == 0
        assert entry.value == 0

    def test_market_item_defaults(self) -> None:
        item = MarketItem.from_dict({})
        assert item.item_id == 0
        assert item.seller is None
