# hOn

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
[![CI][ci-shield]][ci]
[![Maintenance][maintenance-shield]][maintenance]
[![Project Maintenance][maintainer-shield]][maintainer]
[![hassfest validation][hassfest-shield]][hassfest]

Home Assistant component supporting all devices integrated with hOn cloud. The only option to have the climate compatibility.

## Features

- Climate control (Haier / Candy / Hoover heat pumps and ACs)
- Water heaters and heat pump water heaters
- Washing machines, washers-dryers and tumble dryers
- Ovens, dish washers and wine coolers
- Air purifiers
- `hon.start_program` service to launch any available program
- `hon.update_settings` service to update any single setting
- Direct access to all possible services and parameters exposed by the hOn cloud

## Requirements

- Home Assistant >= 2024.1
- An account on the hOn mobile application
- Supported devices: Haier Climate tested

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Add this repo as a custom repository (type: Integration)
3. Search "Haier hOn" and install
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → "hOn"

### Manual

1. Copy `custom_components/hon/` to `<config>/custom_components/`
2. Restart Home Assistant
3. Add the integration from the UI

## Configuration

Configure the integration with your hOn username and password (add → hOn).

After setup, you can open **Options** on the config entry to adjust the polling
interval (default 60 s, range 30–3600 s). Reauthentication is handled through
the UI when your credentials expire.

You can launch any available program by using a dedicated service: `hon.start_program`.
To get all the details about each program, you can go to the device and click on `Get programs details`
![Get programs details](/images/device.jpg)

You will receive one notification per program, you just need to look and click at the notificaiton bell ![Bell](/images/bell.jpg)

Now you you can see all programs and all possible settings value. Have fun!
![Bell](/images/notification.jpg)

## Supported devices

This integration has been tested with the following devices.

### Climate

- AS07TS4HRA-M
- AS25XCAHRA and AS35XCAHRA in 3x1 and 1x1 configuration with one/two outdoor units
- AS35TEDHRA(M1) and AS25TEDHRA(M1) in 2x1 configuration with one outdoor unit
- AS35S2SF1FA-WH and AS25S2SF1FA-WH in 2x1 configuration with one outdoor unit
- AS50S2SF2FA-1/1U50S2SJ2FA
- AD50S2SS1FA(H)

### Oven

- Candy Oven - FCT825XL WIFI Model

### Washing Machine

- HW 49AMC/1-80
- HW90-B14959S8U1
- hoover HWPDQ 49AMBC/1-S
- HW80-B14959TU1DE
- HW110-B14979U1

### Wine Cooler

- HWS42GDAU1
- HWS77GDAU1

### Dish Washer

- XIB 6B2D3FB
- HF 5E5D0FW-17

### WashDryer Machine

- HDQ 496AMBS/1-S

### Tumble Dryer

- Hoover H-Dry 350, 9 kg Condenser Tumble Dryer HRE C9TBE-80
- haier HD80-A3959
- HRE H9A2TE-S
- HLEH10A2TCEX-17
- HD90-A3Q979U1-S
- Candy ROE H9A3TCEX-S

### Air Purifier

- hoover HHP30C011 (Air Purifier 300)
- hoover HHP50CA011 (Air Purifier 500)

### Heat Pump Water Heater

- Haier HP150M8-9 (only programs are working)

### Air to Water Heat Pump

- Haier Monobloc GT R290

## Credits

This integration is based on the original work of gvigroux. Thanks to him for his contribution to the Home Assistant hOn community.

## Troubleshooting

Enable debug logging for the integration:

```yaml
logger:
  default: info
  logs:
    custom_components.hon: debug
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)

<!-- Badges -->
[releases-shield]: https://img.shields.io/github/release/foXaCe/hon.svg?style=for-the-badge
[releases]: https://github.com/foXaCe/hon/releases
[license-shield]: https://img.shields.io/github/license/foXaCe/hon.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[ci-shield]: https://img.shields.io/github/actions/workflow/status/foXaCe/hon/ci.yml?branch=main&style=for-the-badge
[ci]: https://github.com/foXaCe/hon/actions/workflows/ci.yml
[hassfest-shield]: https://img.shields.io/github/actions/workflow/status/foXaCe/hon/hassfest.yml?branch=main&style=for-the-badge&label=hassfest
[hassfest]: https://github.com/foXaCe/hon/actions/workflows/hassfest.yml
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg?style=for-the-badge
[maintenance]: #
[maintainer-shield]: https://img.shields.io/badge/maintainer-%40foXaCe-blue.svg?style=for-the-badge
[maintainer]: https://github.com/foXaCe
