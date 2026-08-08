# Architecture

## Flux de données

```
hOn Cloud API  →  HonConnection (custom_components/hon/hon.py)
                      │
                      ▼
              HonBaseCoordinator (base.py)
                      │
                ┌─────┼──────┬──────────┐
                ▼     ▼      ▼          ▼
           Climate  Sensor  Switch   WaterHeater ...
        (climate.py) (sensor.py) (switch.py) (water_heater.py)
```

- `hon.py` : classe `HonConnection` — gestion de l'authentification hOn (CIAM), tokens, session HTTP et pool de coordinators.
- `base.py` : `HonBaseCoordinator` — DataUpdateCoordinator partagé, polling des états et des paramètres.
- `device.py` : entité appareil générique (mac, type, modèle, marque).
- `parameter.py` : description des paramètres hOn.
- `command.py` : exécution des commandes/programmes.
- `const.py` : constantes (API URL, version d'app, codes appareils, traductions des modes).
- `config_flow.py` : configuration UI (email/mot de passe).

## Entités

Chaque plateforme (climate, sensor, switch, select, number, button, binary_sensor, water_heater)
mappe les champs de la réponse hOn vers des entités Home Assistant.
