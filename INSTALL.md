# Quick Installation Guide

## 🚀 Install in Home Assistant

### Method 1: Manual Installation
1. Copy the entire `custom_components/felicity_solar/` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant  
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "Felicity Solar"
5. Enter your credentials:
   - **Username**: Your Felicity Solar email
   - **Password Hash**: Your encrypted password hash (from network inspection)
   - **Scan Interval**: `30` seconds (default)
   
   **Note**: Plant ID is automatically detected from your account!

### Method 2: HACS Installation (Future)
1. Add this repository as a custom repository in HACS
2. Install "Felicity Solar" from HACS
3. Restart Home Assistant
4. Follow setup steps from Method 1, step 3 onwards

## 📊 Sensors Created

After setup, you'll get these sensors:

### Plant Overview
- `sensor.felicity_solar_current_power` - Real-time power (37W currently)
- `sensor.felicity_solar_today_energy` - Daily energy (14.58 kWh today)  
- `sensor.felicity_solar_total_energy` - Lifetime energy (14.58 kWh total)

### PV String Details  
- `sensor.felicity_solar_pv1_voltage` - String 1 voltage (101.20V)
- `sensor.felicity_solar_pv1_current` - String 1 current (0.30A) 
- `sensor.felicity_solar_pv1_power` - String 1 power (33W)
- `sensor.felicity_solar_pv2_voltage` - String 2 voltage (103.90V)
- `sensor.felicity_solar_pv2_current` - String 2 current (0.00A)
- `sensor.felicity_solar_pv2_power` - String 2 power (2W)

### Combined
- `sensor.felicity_solar_total_pv_power` - Total PV power (35W)

## 🔧 Troubleshooting

### If sensors show "Unavailable":
1. Check Home Assistant logs for errors
2. Verify your credentials are correct
3. Ensure internet connectivity to Felicity Solar API
4. Try restarting the integration

### How to get your Password Hash:
1. Open browser developer tools (F12)
2. Go to Network tab
3. Login to Felicity Solar website
4. Find the login request in network tab
5. Copy the "password" value from the request body - this is your password hash

### If setup fails:
1. Check the exact error message in logs
2. Verify your email/password hash work with the test script
3. Ensure you're using the correct password hash format

## 📈 Energy Dashboard Integration

The energy sensors (`today_energy`, `total_energy`) will automatically appear in Home Assistant's Energy Dashboard for tracking your solar production!

## ✅ Tested & Working

- ✅ Authentication with token refresh
- ✅ Real-time power monitoring  
- ✅ Daily/total energy tracking
- ✅ Individual PV string monitoring
- ✅ Automatic updates every 30 seconds
- ✅ Error handling & recovery