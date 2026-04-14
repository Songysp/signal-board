# SignalBoard Architecture And Status

## Project Identity

- Project name: `SignalBoard`
- Kakao channel/service label: `부동산알리미`

SignalBoard is not just a notification tool. The long-term product is a learning-oriented asset insight platform that helps people understand markets by combining:

1. Signal
- Detect meaningful changes fast.
- Examples: new listings, price changes, rates, gold, stocks, macro indicators.

2. Board
- Put multiple signals on one surface so users can compare and interpret them.
- Real estate, gold, stocks, and macro data should eventually connect in one dashboard.

3. Learning
- Explain why a number matters, not just what changed.
- Future output includes insight cards, trend summaries, and beginner-friendly commentary.

The final product direction is:

- alerting for change detection
- dashboards for understanding trends
- learning content for market study

## Current MVP Goal

The current MVP is intentionally narrow:

- detect new listings from a Naver saved search URL
- send Kakao self-message alerts

In plain terms:

- if a listing that matches a user-defined Naver search appears for the first time,
- SignalBoard should notify the user through KakaoTalk as quickly as possible

## Current Scope

Implemented now:

1. SignalBoard project is separated into its own repo and folder.
2. Kakao token management and self-message sending are implemented.
3. Naver saved search URL parsing is implemented for:
- `fin.land.naver.com`
- `new.land.naver.com`
- `m.land.naver.com`
4. New-version `fin.land` URLs are normalized into structured filters.
5. Structured filters are bridged into Naver mobile listing requests.
6. New listing diff logic is implemented.
7. PostgreSQL storage schema and repository functions are implemented.
8. CLI-based manual preview and polling are implemented.
9. File-based polling without PostgreSQL is implemented for fast local MVP testing.
10. Docker Compose local PostgreSQL is configured.
11. DB-backed repeated polling is available through `poll-loop`.
12. CLI fetch/DB/Kakao failures are converted into operator-friendly messages.
13. Minimal FastAPI surface is available for watches, polling, alerts, preview, and Kakao test sends.

Not implemented yet:

1. production service/daemon runner
2. thin web management UI
3. production-ready API surface and installed API dependencies
4. Kakao friend send / Kakao channel send
5. dashboard screens
6. non-real-estate economic data ingestion

## Current Working Features

### Kakao

Implemented:

- OAuth code exchange
- refresh token handling
- token file persistence
- Kakao self-message sending
- Kakao profile verification

Current policy:

- Kakao self-message is the active notification path
- friend-send and channel-send are deferred

### Naver Search Collection

Implemented:

- parse new `fin.land` URLs
- parse legacy `new.land` URLs
- parse mobile `m.land` URLs
- normalize filters into a common internal model
- resolve regional search context from map center coordinates
- convert normalized search filters into Naver mobile article queries
- fetch listing JSON from Naver mobile endpoints
- parse listing IDs, title, price, trade type, area, floor, and raw payload

Important detail:

- new `fin.land` URLs are not fetched directly from the unstable internal web API
- instead, SignalBoard parses the new URL, resolves region context, and fetches listings through the mobile listing path
- this is more stable for the current MVP, but still not guaranteed against future Naver changes

### Diff And Alert Flow

Implemented:

1. first poll creates a baseline only
2. second and later polls detect listings not seen before
3. only new listing IDs trigger alerts
4. alert messages include:
- title
- price
- trade type
- area
- floor
- link

## Storage Model

Primary storage target:

- PostgreSQL

Current core tables:

- `watch_targets`
- `listing_snapshots`
- `listing_current_state`
- `alert_events`

Purpose:

- `watch_targets`: saved search URL, label, normalized filter payload, activation state
- `listing_snapshots`: every poll result as a point-in-time snapshot
- `listing_current_state`: latest known state per listing
- `alert_events`: deduplicated new-listing alert history

Temporary no-infra fallback:

- local JSON state file for single-URL polling

This fallback exists so the MVP can be used before PostgreSQL is fully wired in local runtime.

## Current CLI Surface

Implemented commands include:

- `health`
- `show-config`
- `kakao-login`
- `kakao-exchange-code`
- `kakao-refresh`
- `kakao-me`
- `send-test-kakao`
- `inspect-search-url`
- `preview-search`
- `poll-url`
- `init-db`
- `db-check`
- `add-watch`
- `list-watches`
- `poll`
- `poll-loop`

## Current API Surface

Install optional API dependencies:

- `python -m pip install -e .[api]`

Run locally:

- `python -m uvicorn app.main:app --reload`

Implemented endpoints:

- `GET /health`
- `GET /watches`
- `POST /watches`
- `POST /poll`
- `GET /alerts`
- `POST /preview-search`
- `POST /kakao/test`

Practical usage today:

1. `preview-search`
- fetch one Naver URL immediately and print parsed listings

2. `poll-url`
- poll one URL without PostgreSQL
- create a baseline file on first run
- detect only newly seen listings on later runs
- optionally send Kakao alerts

3. `poll`
- PostgreSQL-backed polling for registered watches
- depends on a running database

4. `poll-loop`
- PostgreSQL-backed repeated polling
- intentionally simple while-loop runner for the MVP

## Search URL Strategy And Limits

Current strategy:

- accept user-provided Naver search URLs
- parse them into a structured filter model
- use that model to fetch actual listings

Known limits:

- Naver may change URL formats or internal mobile endpoints
- not every visible filter has a clean 1:1 transport mapping
- some filters are currently approximated rather than perfectly preserved
- region resolution is currently derived from coordinate-based reverse lookup plus Naver mobile search flow

So the MVP is fast and usable, but not fully canonical yet.

## API And UI Direction

The product is still API-first in design, even though the UI is not built yet.

Planned structure:

- `core`: collection, diff, alerting, storage logic
- `api`: shared interface for web and future mobile
- `web`: minimal management UI first
- `mobile`: later app client

Current status:

- core is partially implemented
- API is still minimal
- web UI has not started

## Future Vision

SignalBoard is expected to expand into:

### Real Estate

- new listing alerts
- price change tracking
- favorite complex tracking
- regional mood summaries
- complex-level price trend views

### Asset Indicators

- gold
- Korean and US market indices
- FX
- rates
- CPI, unemployment, volume, and other macro indicators

### Learning Dashboard

- daily market summary
- 7-day / 30-day / 1-year change cards
- cross-asset comparisons
- "why this matters" explainers
- beginner-friendly narrative screens

### Content Layer

- automated insight cards
- weekly briefings
- market commentary
- related indicator recommendations
- “numbers to watch together” style connections

The intended end state is:

- Kakao alerts for change detection
- dashboards for trend understanding
- explanation layers for learning

## Recommended Next Steps

In order of priority:

1. finish PostgreSQL local connection and end-to-end DB-backed polling
2. build the first minimal web management UI
