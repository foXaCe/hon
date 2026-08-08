# Configuration

Configure the integration with your hOn username and password.

## Services

### `hon.start_program`

Launch any available program on an appliance.

1. Go to the device and click on `Get programs details`
2. You will receive one notification per program — look and click at the notification bell
3. Select the program and its settings values, then launch

### `hon.update_settings`

Update any single setting on an appliance.

## Debug logging

```yaml
logger:
  default: info
  logs:
    custom_components.hon: debug
```
