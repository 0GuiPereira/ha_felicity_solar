# Installation Guide

### Method 1: HACS Installation
1. Add this repository as a custom repository in HACS
<pre>
https://github.com/0GuiPereira/ha_felicity_solar
</pre>
2. Install "Felicity Solar" from HACS
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "Felicity Solar"
6. Enter your credentials:
   - **Username**: Your Felicity Solar email
   - **Password Hash**: Your encrypted password hash (from network inspection)
   - **Scan Interval**: `30` seconds (default)
   
   **Note**: Plant ID is automatically detected from your account!

### Method 2: Manual Installation
1. Copy the entire `custom_components/felicity_solar/` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant  
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "Felicity Solar"
5. Enter your credentials:
   - **Username**: Your Felicity Solar email
   - **Password Hash**: Your encrypted password hash (from network inspection)
   - **Scan Interval**: `30` seconds (default)
   
   **Note**: Plant ID is automatically detected from your account!

## How to get your Password Hash:
1. Open browser developer tools (F12)
2. Go to Network tab
3. Login to Felicity Solar website
4. Find the login request in network tab
5. Copy the "password" value from the request body - this is your password hash

