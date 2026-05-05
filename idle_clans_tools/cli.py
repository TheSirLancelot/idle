"""Command-line interface for clanlytics.

Examples::

    # Look up a player
    python -m idle_clans_tools player SomeUsername

    # Look up a clan
    python -m idle_clans_tools clan MyClan

    # Show the top 10 on the total-XP leaderboard
    python -m idle_clans_tools leaderboard total --top 10

    # Query market listings for an item
    python -m idle_clans_tools market "Iron Ore"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import IdleClansClient
from .api.exceptions import IdleClansAPIError, NetworkError, NotFoundError, RateLimitError
from .api.levels import level_for_experience, level_progress_percent
from .api.models import GameItem


def _format_optional(value: object) -> str:
    return str(value) if value is not None and value != "" else "(none)"


def _print_mapping(title: str, values: dict[str, int]) -> None:
    if not values:
        return
    print(f"\n{title}:")
    for name, value in sorted(values.items(), key=lambda item: item[0].casefold()):
        print(f"  {name:<28} {value:>12,}")


def _print_skills(values: dict[str, int]) -> None:
    if not values:
        return
    print("\nSkills:")
    print(f"  {'Skill':<28} {'Level':>5} {'Next':>8} {'XP':>12}")
    for name, xp in sorted(values.items(), key=lambda item: item[0].casefold()):
        progress = f"{level_progress_percent(xp):.2f}%"
        print(f"  {name:<28} {level_for_experience(xp):>5} {progress:>8} {xp:>12,}")


def _print_equipment(values: dict[str, int], item_lookup: dict[int, GameItem]) -> None:
    if not values:
        return
    print("\nEquipment:")
    print(f"  {'Slot':<16} {'Item':<32}")
    for slot, item_id in sorted(values.items(), key=lambda item: item[0].casefold()):
        item = item_lookup.get(item_id)
        if item_id < 0:
            item_name = "(empty)"
        elif item is None:
            item_name = "(unknown)"
        else:
            item_name = item.display_name
        print(f"  {slot:<16} {item_name:<32}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clanlytics",
        description="CLI tools for the Idle Clans public API.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # ---- player -----------------------------------------------------------
    player_parser = subparsers.add_parser("player", help="Look up a player profile.")
    player_parser.add_argument("username", help="In-game player username.")

    # ---- clan -------------------------------------------------------------
    clan_parser = subparsers.add_parser("clan", help="Look up a clan.")
    clan_parser.add_argument("clan_name", help="Exact clan name.")
    clan_parser.add_argument(
        "--members",
        action="store_true",
        help="Also show the clan member list.",
    )

    # ---- leaderboard -------------------------------------------------------
    lb_parser = subparsers.add_parser("leaderboard", help="Show leaderboard rankings.")
    lb_parser.add_argument(
        "category",
        help=("Leaderboard stat key (e.g. total_level, attack, mining, woodcutting)."),
    )
    lb_parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Number of entries to display (default: 10).",
    )
    lb_parser.add_argument(
        "--page",
        type=int,
        default=1,
        metavar="PAGE",
        help="Page number (default: 1).",
    )

    # ---- market ------------------------------------------------------------
    market_parser = subparsers.add_parser("market", help="Query player market listings.")
    market_parser.add_argument(
        "item_name",
        nargs="?",
        default=None,
        help="Filter by item name (optional).",
    )

    # ---- game-data ---------------------------------------------------------
    game_data_parser = subparsers.add_parser(
        "gamedata",
        help="List or export static game-data sections.",
    )
    game_data_parser.add_argument(
        "--list-sections",
        action="store_true",
        help="List top-level game-data sections.",
    )
    game_data_parser.add_argument(
        "--section",
        default=None,
        help="Top-level section name to export (for example: Items).",
    )
    game_data_parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path for exported data.",
    )

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_player(client: IdleClansClient, args: argparse.Namespace) -> None:
    profile = client.get_player_profile(args.username)
    try:
        item_lookup = client.get_item_lookup()
    except IdleClansAPIError:
        item_lookup = {}

    print(f"Player:           {profile.username}")
    print(f"Game mode:        {_format_optional(profile.game_mode)}")
    print(f"Guild/Clan:       {_format_optional(profile.clan_name)}")
    print(f"Combat level:     {profile.combat_level}")
    print(f"Total experience: {profile.total_experience:,}")
    print(f"Hours offline:    {_format_optional(profile.hours_offline)}")
    print(f"Logout task type: {_format_optional(profile.task_type_on_logout)}")
    print(f"Logout task name: {_format_optional(profile.task_name_on_logout)}")
    print(f"Active server ID: {_format_optional(profile.active_server_id)}")

    _print_skills(profile.skills)
    _print_equipment(profile.equipment, item_lookup)
    _print_mapping("Enchantment boosts", profile.enchantment_boosts)
    _print_mapping("Upgrades", profile.upgrades)
    _print_mapping("PvM stats", profile.pvm_stats)


def _cmd_clan(client: IdleClansClient, args: argparse.Namespace) -> None:
    info = client.get_clan_info(args.clan_name)
    print(f"Clan:             {info.name}")
    if info.tag:
        print(f"Tag:              {info.tag}")
    if info.leader:
        print(f"Leader:           {info.leader}")
    print(f"Members:          {info.member_count}")
    if info.is_recruiting is not None:
        print(f"Recruiting:       {'yes' if info.is_recruiting else 'no'}")
    if info.language:
        print(f"Language:         {info.language}")
    if info.category:
        print(f"Category:         {info.category}")
    if info.total_experience:
        print(f"Total experience: {info.total_experience:,}")
    if info.description:
        print(f"Message:          {info.description}")

    if args.members:
        members = client.get_clan_members(args.clan_name)
        if members:
            print("\nMember list:")
            for m in members:
                print(f"  [{m.rank:<12}] {m.username:<24} {m.total_experience:>12,} XP")
        else:
            print("\nNo members found.")


def _cmd_leaderboard(client: IdleClansClient, args: argparse.Namespace) -> None:
    entries = client.get_leaderboard(args.category, page=args.page, page_size=args.top)
    if not entries:
        print(f"No leaderboard data found for category '{args.category}'.")
        return

    print(f"Leaderboard: {args.category} (page {args.page})")
    print(f"{'Rank':<6} {'Username':<24} {'Value':>15}")
    print("-" * 47)
    for entry in entries[: args.top]:
        print(f"{entry.rank:<6} {entry.username:<24} {entry.value:>15,}")


def _cmd_market(client: IdleClansClient, args: argparse.Namespace) -> None:
    items = client.get_market_items(item_name=args.item_name)
    if not items:
        label = f"'{args.item_name}'" if args.item_name else "all items"
        print(f"No market listings found for {label}.")
        return

    header = f"Market listings{' for ' + args.item_name if args.item_name else ''}"
    print(header)
    print(f"{'Item':<30} {'Price':>10} {'Qty':>8} {'Seller':<24}")
    print("-" * 74)
    for item in items:
        seller = item.seller or "(unknown)"
        print(f"{item.item_name:<30} {item.price:>10,} {item.quantity:>8,} {seller:<24}")


def _cmd_gamedata(client: IdleClansClient, args: argparse.Namespace) -> None:
    show_sections = args.list_sections or not args.section
    if show_sections:
        sections = client.list_game_data_sections()
        print("Game-data sections:")
        for name in sections:
            print(f"  - {name}")
        if not args.section:
            return

    payload = client.get_game_data_section(args.section)
    rendered = json.dumps(payload, indent=2, sort_keys=True)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote section '{args.section}' to {output_path}")
        return

    print(rendered)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_HANDLERS = {
    "player": _cmd_player,
    "clan": _cmd_clan,
    "leaderboard": _cmd_leaderboard,
    "market": _cmd_market,
    "gamedata": _cmd_gamedata,
}


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and dispatch to the correct handler."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    client = IdleClansClient()

    try:
        _HANDLERS[args.command](client, args)
    except NotFoundError as exc:
        print(f"Not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except RateLimitError as exc:
        print(f"Rate limited: {exc}", file=sys.stderr)
        sys.exit(1)
    except NetworkError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        sys.exit(1)
    except IdleClansAPIError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
