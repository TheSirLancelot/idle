# Idle Clans API Endpoint Reference

This document summarizes endpoints from the live Idle Clans OpenAPI spec.

Source: `https://query.idleclans.com/swagger/v1/swagger.json`  
Snapshot date: 2026-05-05

## Chat

| Method | Endpoint         | What it is used for                                                      |
| ------ | ---------------- | ------------------------------------------------------------------------ |
| GET    | /api/Chat/recent | Fetch recent public chat messages, with channel include/exclude filters. |

## Clan

| Method | Endpoint                                          | What it is used for                                                        |
| ------ | ------------------------------------------------- | -------------------------------------------------------------------------- |
| GET    | /api/Clan/logs/clan/{name}                        | Fetch clan-wide activity logs/messages.                                    |
| GET    | /api/Clan/logs/clan/{clanName}/{playerName}       | Fetch logs for a specific player within a clan.                            |
| GET    | /api/Clan/recruitment/{clanName}                  | Fetch clan recruitment/profile data (members, tag, recruiting info, etc.). |
| GET    | /api/Clan/most-active                             | List most active clans based on query criteria.                            |
| GET    | /api/Clan/{clanName}/experience                   | Get clan experience totals and contribution summary over a time window.    |
| GET    | /api/Clan/{clanName}/experience/timeline          | Get clan experience progression over time (interval timeline).             |
| GET    | /api/Clan/experience/top                          | Get top clans by gained experience with per-skill breakdown.               |
| GET    | /api/Clan/experience/top/{skill}                  | Get top clans for a specific skill by gained experience.                   |
| GET    | /api/Clan/{clanName}/experience/player/{username} | Get one player's XP contribution within a clan/time window.                |

## ClanCup

| Method | Endpoint                                             | What it is used for                                                      |
| ------ | ---------------------------------------------------- | ------------------------------------------------------------------------ |
| GET    | /api/ClanCup/standings/{clanName}                    | Get a clan's standings across all current/selected Clan Cup objectives.  |
| GET    | /api/ClanCup/standing/{clanName}                     | Get a clan's standing for one Clan Cup objective.                        |
| GET    | /api/ClanCup/top-clans/current                       | Get current top clans per Clan Cup objective.                            |
| GET    | /api/ClanCup/top-clans/previous                      | Get previous cup top clans per objective.                                |
| GET    | /api/ClanCup/top-clans/date                          | Get top clans for the cup tied to a specific end date.                   |
| GET    | /api/ClanCup/leaderboard/{gameMode}/totalPoints      | Get overall Clan Cup points leaderboard for a game mode.                 |
| GET    | /api/ClanCup/leaderboard/{gameMode}/{category}       | Get Clan Cup leaderboard for a single category/objective in a game mode. |
| GET    | /api/ClanCup/leaderboard/{gameMode}/clans/{clanName} | Get a specific clan's Clan Cup standing for a game mode.                 |

## Configuration

| Method | Endpoint                          | What it is used for                                                 |
| ------ | --------------------------------- | ------------------------------------------------------------------- |
| GET    | /api/Configuration/build-versions | Fetch required/latest build versions and config version info.       |
| GET    | /api/Configuration/game-data      | Fetch static game data payload (items, metadata, config-like data). |

## Leaderboard

| Method | Endpoint                                          | What it is used for                                                          |
| ------ | ------------------------------------------------- | ---------------------------------------------------------------------------- |
| GET    | /api/Leaderboard/profile/{leaderboardName}/{name} | Fetch profile data for a player or clan in a specific leaderboard namespace. |
| GET    | /api/Leaderboard/top/{leaderboardName}/{name}     | Fetch ranked leaderboard entries for a specific stat/category.               |

## News

| Method | Endpoint         | What it is used for             |
| ------ | ---------------- | ------------------------------- |
| GET    | /api/news/latest | Fetch latest game/news updates. |

## Player

| Method | Endpoint                              | What it is used for                                                     |
| ------ | ------------------------------------- | ----------------------------------------------------------------------- |
| GET    | /api/Player/clan-logs/{name}          | Fetch a player's clan-related logs across clans.                        |
| GET    | /api/Player/profile/{name}            | Fetch a full player profile.                                            |
| GET    | /api/Player/profile/simple/{username} | Fetch a lightweight player profile (useful for activity status fields). |
| GET    | /api/Player/activities                | Fetch current activities for multiple players in one request (batch).   |

## PlayerMarket

| Method | Endpoint                                                     | What it is used for                                                |
| ------ | ------------------------------------------------------------ | ------------------------------------------------------------------ |
| GET    | /api/PlayerMarket/items/prices/latest/{itemId}               | Get latest price snapshot for one item.                            |
| GET    | /api/PlayerMarket/items/prices/latest/comprehensive/{itemId} | Get detailed price distribution and rolling averages for one item. |
| GET    | /api/PlayerMarket/items/prices/latest                        | Get latest price snapshot for all items.                           |
| GET    | /api/PlayerMarket/items/prices/history/{itemId}              | Get historical prices for one item over a selected period.         |
| GET    | /api/PlayerMarket/items/prices/history                       | Get historical prices for all traded items over a selected period. |
| GET    | /api/PlayerMarket/items/prices/history/value                 | Get highest-value trades over a selected period.                   |
| GET    | /api/PlayerMarket/items/volume/history                       | Get top items by trade volume over a selected period.              |

## Server

| Method | Endpoint         | What it is used for                                     |
| ------ | ---------------- | ------------------------------------------------------- |
| GET    | /api/Server/info | Fetch active server status/load and recommended server. |

## Startup

| Method | Endpoint          | What it is used for                                                        |
| ------ | ----------------- | -------------------------------------------------------------------------- |
| GET    | /api/Startup/info | Fetch startup bootstrap data (for example build versions and server info). |

## Notes

- Most endpoints are public `GET` endpoints.
- Some operations may support optional query parameters (pagination, period windows, filters).
- The OpenAPI spec also defines an `ApiKey` security scheme (`X-Api-Key`) for protected endpoints, but the endpoints listed above are documented as readable in the public schema.
