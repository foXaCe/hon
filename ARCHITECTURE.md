# Architecture

## Flux de données

```
hOn Cloud API  →  HonConnection (custom_components/hon/api/client.py)
                      │
                      ▼
              HonBaseCoordinator (coordinator.py)
                DataUpdateCoordinator[HonDevice]
                      │
                ┌─────┼──────┬──────────┬───────┐
                ▼     ▼      ▼          ▼       ▼
           Climate  Sensor  Switch  WaterHeater Number/Select
```

Le cœur du fonctionnement :

- **`api/client.py`** : `HonConnection` — authentification hOn CIAM (PKCE), gestion des tokens, session aiohttp partagée (`async_get_clientsession`), timeout 30 s, retry à backoff exponentiel, refresh token sur 401, pool de coordinators (`async_get_coordinator`). Aucun credential loggé.
- **`api/exceptions.py`** : exceptions typées (`HonAuthenticationError`, `HonConnectionError`, `HonRateLimitError`) mappées sur `ConfigEntryAuthFailed`/`ConfigEntryNotReady`/`UpdateFailed`.
- **`api/models.py`** : dataclasses des réponses API (`HonAppliance`).
- **`coordinator.py`** : `HonBaseCoordinator(DataUpdateCoordinator[HonDevice])` — un par appareil. `_async_setup` charge commandes + statistiques une fois ; `_async_update_data` rafraîchit le contexte (`UpdateFailed` sur erreur). `unique_id_prefix` fournit le préfixe d'UID `{entry.unique_id}_{mac}`.
- **`devices/base.py`** : `HonBaseEntity` — comportement commun (device_info, `has_entity_name`, UID préfixé) + classes de base sensor/binary_sensor/switch.
- **`devices/`** : une classe d'entité par plateforme (`sensor.py` = 38 classes de capteurs dynamiques selon les attributs API, `climate.py`, `water_heater.py`, `switch.py`, `number.py`, `select.py`, `button.py`, `device.py` = modèle appareil, `base.py`).
- **`parameter.py` / `command.py`** : modèles des paramètres hOn (range, enum, fixed) et des commandes/programmes.
- **`helpers.py`** : fonctions pures (`snake_case`, `get_key`, `minutes_until`).
- **`__init__.py`** : setup/unload de l'entry (`entry.runtime_data`), `async_migrate_entry` (v1→v2), enregistrement des 28 services.
- **`config_flow.py`** : ConfigFlow (user/reauth/reconfigure) + OptionsFlow (`update_interval`).
- **`diagnostics.py`** : `async_get_config_entry_diagnostics` — snapshot entry/appliances/coordinators/devices/entities, secrets redactés.
- **`const.py`** : toutes les constantes (API URL, types d'appareils, mappings modes).

## Ajouter un nouveau type de device

1. Dans `const.py`, ajouter l'entrée `APPLIANCE_TYPE` + `APPLIANCE_DEFAULT_NAME` si nécessaire.
2. Dans `devices/sensor.py` (ou `binary_sensor.py`), ajouter une classe d'entité lisant les attributs API du device.
3. Dans la plateforme `sensor.py`/`binary_sensor.py`, ajouter la garde `device.has(...)` dans `async_setup_entry`.
4. Ajouter les clés de traduction dans `strings.json` + `translations/{en,fr}.json`.

## Ajouter une nouvelle plateforme

1. Créer `devices/<plateforme>.py` (classe d'entité) + `<plateforme>.py` (rôle `async_setup_entry` uniquement).
2. Ajouter le nom dans `PLATFORMS` (`const.py`).
3. Ajouter `entity.<plateforme>.*` dans les traductions.

## Points d'extension

- Nouveaux types d'appareils : `devices/` + `const.APPLIANCE_TYPE`.
- Nouveaux services : `__init__.py` (handler) + `services.yaml` + traductions.
- Nouveaux capteurs : `devices/sensor.py` + garde dans `sensor.py`.

## Tests

- `tests/` : 402 tests, coverage 96 %. Fixtures partagées dans `tests/conftest.py` et `tests/devices/conftest.py`.
- API mockée via `mock_connection` (aucun appel réseau réel).
- `python3 -m pytest tests/ --cov=custom_components/hon --cov-report=term-missing`
