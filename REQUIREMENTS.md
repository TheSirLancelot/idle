# clanlytics requirements

This document captures the current project requirements and development standards.
Treat it as a living document and update it as scope evolves.

## 1. Product goal

Build a clean, beginner-friendly Python toolkit for the Idle Clans public API that can be reused by future interfaces (CLI, web app, Discord bot).

## 2. Functional requirements

1. Provide a Python API client that supports:
- Player profile lookup
- Clan lookup and member retrieval
- Leaderboard retrieval
- Market data retrieval

2. Keep API concerns separate from interface concerns.
- API code lives in idle_clans_tools/api
- CLI code lives in idle_clans_tools/cli.py

3. Expose a CLI with commands for:
- player lookup
- clan lookup
- leaderboard lookup
- market lookup
- Primary command alias is `ic` (with `clanlytics` as the full command name)

4. Implement basic API error handling for:
- Missing resources (404)
- Rate limits (429)
- Bad/unexpected responses
- Network failures (timeouts/connection failures)

## 3. Non-functional requirements

1. Python 3.10+
2. Type hints on public APIs where practical
3. Readable, extension-friendly naming and structure
4. Tests must not depend on live network access

## 4. Testing requirements

1. Use pytest for unit tests
2. Mock HTTP calls in client tests
3. Cover success and failure paths for each client method
4. Validate endpoint parameter forwarding where relevant

## 5. Development environment requirements

1. Use a local virtual environment at .venv
2. Install project with dev extras:
- pip install -e ".[dev]"

## 6. Code quality requirements

1. Ruff is the project linting and formatting tool
2. Required checks before PR merge:
- python -m ruff check .
- python -m ruff format --check .
- python -m pytest

## 7. Change management

1. Update this document when adding new features or architectural constraints
2. Keep README aligned with actual commands, dependencies, and endpoints
