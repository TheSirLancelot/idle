"""Page renderers exposed for the Streamlit app router."""

from idle_clans_tools.ui.pages.clan import render_clan_lookup
from idle_clans_tools.ui.pages.game_data_browser import render_game_data_browser
from idle_clans_tools.ui.pages.leaderboards import render_leaderboards
from idle_clans_tools.ui.pages.market import render_market
from idle_clans_tools.ui.pages.player import render_player_lookup

__all__ = [
    "render_player_lookup",
    "render_clan_lookup",
    "render_leaderboards",
    "render_market",
    "render_game_data_browser",
]
