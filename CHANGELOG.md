# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.4] - 2026-08-11

### Performance

- Config entry setup ~61% faster (≈3.4s → ≈1.3s) on a warm boot. Each
  appliance's command catalogue and statistics are persisted in a store keyed
  by firmware and app version, so only the live requests block the setup; the
  cached payloads are refreshed in the background afterwards. A firmware
  change (or an integration app-version bump) invalidates the cache and falls
  back to the blocking fetch.
- The appliance list is persisted too, so a warm boot probes the stored
  session and fetches the device contexts concurrently instead of waiting for
  the fresh list. The probe result then reconciles it: an appliance added
  since the last boot gets a blocking first refresh, a removed one is pruned
  and never blocks the entry.
- Dropped the `python-dateutil` requirement (its only use is now covered by
  Home Assistant's own datetime helpers), so HA no longer resolves it at
  startup.

### Fixed

- After a re-authentication, a retried request kept sending the auth headers
  captured when the call started — that is, the stale tokens. They are now
  rebuilt on every attempt.
- Concurrent requests hitting an expired session no longer each trigger their
  own login: re-authentication is serialized and deduplicated, so the losers
  of the race retry with the tokens the winner obtained.
- Loading the command catalogue no longer fails on payloads that omit
  `dictionaryId`.

## [0.9.3] - 2026-08-10

### Fixed

- Appliance entities (selects, buttons…) stuck `unavailable` when the
  persisted CIAM session was revoked with an HTTP 403: the session-restore
  path now falls back to a full login for 401, 403 and 429 (not only 401),
  and `_async_request` treats a 403 like a 401 (refresh + retry) so the
  integration recovers instead of looping on "Config entry not ready".

## [0.9.2] - 2026-08-09

### Performance

- Config entry setup ~45% faster (≈4.0s → ≈2.1–2.4s): the device context is
  now fetched in parallel with the commands and statistics during the
  coordinator setup instead of waiting for the first refresh.
- Reuse a persisted CIAM session on boot: fresh `id`/`cognito` tokens are
  written back to the config entry after login and reused at startup, so a
  full PKCE login (3 round-trips) is only needed when the stored tokens are
  rejected. The hOn CIAM does not accept `grant_type=refresh_token`, so a
  stale session still falls back to a full login automatically.

## [0.9.1] - 2026-08-09

### Fixed

- "Get programs details" button no longer created for washing machines and dryers: the start-button was wrongly gated on oven/dishwasher appliance types, so it was missing for any device exposing `startProgram`. The program-details button is now created for every appliance that has the `startProgram` command.

## [0.9.0] - 2026-08-09

### Added

- Modular architecture: `api/` (client, exceptions, models) and `devices/` (per-platform entity classes), `helpers.py`
- `strings.json` (single source of truth for translations), full French translations (was ~5% coverage)
- Options flow with configurable `update_interval` (30–3600 s)
- Reauth and reconfiguration flows
- Diagnostics-ready typed exceptions (`HonAuthenticationError`, `HonConnectionError`, `HonRateLimitError`)
- `number` and `select` platforms (were dead code) with working command sending
- `diagnostics.py` (entry/appliance/coordinator/device/entity snapshot, secrets redacted)
- `system_health.py` (cloud reachability, appliance count, update status)
- Entity names fully localized (FR/EN) via `translation_key`: sensors, binary sensors, switches, buttons
- French translations for the config flow and the options flow
- Button notifications (programs/settings details) localized in French, with translated program titles
- Mode/phase/error entity names added (were state-only translations, no `name`)
- 407 tests, 96 % coverage

### Changed

- `entry.runtime_data` instead of `hass.data[DOMAIN][...]`
- Typed `DataUpdateCoordinator[HonDevice]` with `_async_setup` one-shot loading and `UpdateFailed`
- `unique_id` format now namespaced per config entry: `{entry.unique_id}_{mac}_{key}`
- Config entry version bumped 1 → 2 (automatic migration via `async_migrate_entry`)
- `has_entity_name = True` on all entities
- Appliance contexts loaded in parallel at setup (boot faster than baseline)
- Boot optimized: removed redundant per-platform refreshes (sensor 1×, switch 9×, climate re-first-refresh) and parallelized commands/statistics loading — config entry setup ~4s vs ~9s baseline
- Shared aiohttp session, 30 s timeout, exponential backoff retry, token refresh on 401
- `from __future__ import annotations`, strict typing, docstrings everywhere
- English translations cleaned (broken keys, duplicate states, newline keys)
- Entity names moved from hard-coded English `_attr_name` to `translation_key` (HA resolves FR/EN from translations)
- Service YAML defaults/tools aligned with handlers

### Fixed

- Options flow crash on HA ≥ 2026.7 (overwrote read-only `config_entry`)
- Config flow options handler raised 500 on load (constructor signature mismatch)
- `HonDevice.set` never persisted values (wrote into a recreated dict)
- Orphan services `turn_off_oven`, `turn_off_washingmachine`, `turn_off_purifier` now have handlers
- Deprecated `CONCENTRATION_*` constants replaced with `UnitOfDensity`/`UnitOfRatio`
- `HonBaseChildLockStatus` translation key never applied
- `get_setting` service logged whole device object at WARNING
- Switch `available` logged WARNING on every evaluation
- Log f-strings replaced with lazy `%s` formatting

### Removed

- Dead code: duplicate `async_get_device_ids`, commented-out blocks, unused platform scaffolding
