# clanlytics

A Python toolkit for interacting with the [Idle Clans](https://idleclans.com/) public API.

---

## What is this?

**clanlytics** is a clean, extensible API client and CLI for the
[Idle Clans public query API](https://query.idleclans.com/api-docs/index.html).
It is designed to be a solid foundation that can later power a Discord bot,
web app, or any other front-end.

---

## Current features

- **Player lookup** – fetch a player's profile, XP, combat level, and skills.
- **Clan lookup** – fetch clan recruitment info and the full member list.
- **Leaderboards** – query skill or total-XP leaderboards with pagination.
- **Market** – list current player-market listings, optionally filtered by
  item name.
- **Robust error handling** – custom exceptions for 404s, rate limits (429),
  generic API errors, and network failures.
- **CLI entry point** – run any query straight from your terminal.
- **Full type hints** – every public function is typed for IDE support.
- **pytest test suite** – all client logic is unit-tested with mocked HTTP
  calls (no real network needed).

---

## Planned features

- Discord bot commands built on top of this API layer.
- Caching layer to reduce duplicate API calls.
- Richer skill / item models as the API evolves.
- Web dashboard or REST proxy.

---

## Installation

**Prerequisites:** Python 3.10 or later.

```bash
# Clone the repo
git clone https://github.com/TheSirLancelot/idle.git
cd idle

# Create and activate a virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install in editable mode (includes dev dependencies)
pip install -e ".[dev]"
```

On macOS/Linux, activate the environment with:

```bash
python -m venv .venv
source .venv/bin/activate
```

Or install only the runtime dependencies:

```bash
pip install -e .
```

---

## Running the CLI

After installation the `ic` and `clanlytics` commands are available in your PATH.
You can also run it with `python -m idle_clans_tools`.

```bash
# Look up a player
ic player YourUsername

# Look up a clan
ic clan "Clan Name"

# Show a clan's member list
ic clan "Clan Name" --members

# Show the top 10 on the total level leaderboard
ic leaderboard total_level --top 10

# Show a specific skill leaderboard (page 2)
ic leaderboard woodcutting --top 25 --page 2

# Show all player-market listings
ic market

# Filter market listings by item name
ic market "Iron Ore"
```

---

## Running the tests

```bash
python -m pytest
```

To run with coverage:

```bash
python -m pytest --cov=idle_clans_tools
```

---

## Linting and formatting (Ruff)

Run lint checks:

```bash
python -m ruff check .
```

Apply auto-fixes for lint issues where possible:

```bash
python -m ruff check . --fix
```

Run formatting:

```bash
python -m ruff format .
```

---

## Project structure

```
idle/
├── idle_clans_tools/
│   ├── __init__.py          # Package version
│   ├── __main__.py          # python -m idle_clans_tools entry point
│   ├── cli.py               # argparse CLI
│   └── api/
│       ├── __init__.py      # Public re-exports
│       ├── client.py        # HTTP client wrapper
│       ├── exceptions.py    # Custom exception classes
│       └── models.py        # Typed dataclass models
├── tests/
│   └── test_client.py       # pytest unit tests
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## API reference

The Idle Clans public API is documented at
<https://query.idleclans.com/api-docs/index.html>.

The base URL used by this client is `https://query.idleclans.com`.

| Feature | Endpoint used |
|---|---|
| Player profile | `GET /api/Player/profile/{name}` |
| Clan recruitment info | `GET /api/Clan/recruitment/{clanName}` |
| Clan members | `GET /api/Clan/recruitment/{clanName}` (memberlist) |
| Leaderboard | `GET /api/Leaderboard/top/{leaderboardName}/{name}` |
| Market price snapshot | `GET /api/PlayerMarket/items/prices/latest` |

---

## Contributing

Pull requests are welcome!  Please add or update tests for any new behaviour
and make sure `pytest` passes before opening a PR.
