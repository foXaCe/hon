# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- 406 tests, 96 % coverage

### Changed

- `entry.runtime_data` instead of `hass.data[DOMAIN][...]`
- Typed `DataUpdateCoordinator[HonDevice]` with `_async_setup` one-shot loading and `UpdateFailed`
- `unique_id` format now namespaced per config entry: `{entry.unique_id}_{mac}_{key}`
- Config entry version bumped 1 → 2 (automatic migration via `async_migrate_entry`)
- `has_entity_name = True` on all entities
- Appliance contexts loaded in parallel at setup (boot faster than baseline)
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
