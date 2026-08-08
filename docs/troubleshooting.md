# Troubleshooting

## Enable debug logging

```yaml
logger:
  default: info
  logs:
    custom_components.hon: debug
```

## Common issues

- **Devices not detected** : verify your devices are registered in the hOn mobile application first.
- **Login fails** : double-check your hOn username and password.
- **Programs not working** : some appliances only expose a subset of programs through the cloud.

For persistent issues, open a bug report with the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
