# Felicity Solar Home Assistant Integration

This integration allows you to monitor your Felicity Solar inverter data in Home Assistant.

## Features

The integration provides the following sensors:

- **Current Power**: Real-time power generation (W)
- **Today Energy**: Energy generated today (kWh) 
- **Total Energy**: Total energy generated (kWh)
- **PV String Voltages**: Individual string voltages (V)
- **PV String Currents**: Individual string currents (A)
- **PV String Powers**: Individual string powers (W)
- **Total PV Power**: Combined PV power from all strings (W)

## Installation

### Manual Installation

1. Copy the `custom_components/felicity_solar` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration -> Integrations
4. Click "Add Integration" and search for "Felicity Solar"
5. Enter your plant ID (can be found in the Felicity Solar app/website)

### HACS Installation

1. Add this repository to HACS as a custom repository
2. Install the integration through HACS
3. Restart Home Assistant
4. Follow the manual setup steps from step 3

## Configuration

The integration requires:

- **Username/Email**: Your Felicity Solar account username or email
- **Password Hash**: The encrypted password hash from your Felicity Solar account (not the plain text password)
- **Scan Interval**: How often to update data in seconds (default: 30)

The integration will automatically:
- Detect your plant ID from the API (no manual input needed)
- Handle authentication token management, including automatic token refresh

## API Endpoints Used

The integration uses the following Felicity Solar API endpoints:

1. `/plant/list_plant` - Gets plant information including power and energy data
2. `/device/get_device_realtime_icon_template_info` - Gets real-time device data including PV string details

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

1. Verify your username/email and password are correct
2. Check that your account is activated (contact administrator if not)
3. Ensure your internet connection is stable
4. The integration automatically handles token refresh, but may need to re-login if refresh tokens expire

### No Data

If sensors show unavailable or no data:

1. Verify your plant ID is correct
2. Check that your solar system is online
3. Ensure the API endpoints are accessible from your network

## Development

To test the API endpoints without Home Assistant, run:

```bash
python test_api.py
```

This will test the basic API calls and show you the available data structure.

## Contributing

Issues and pull requests are welcome on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.