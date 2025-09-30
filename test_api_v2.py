#!/usr/bin/env python3
"""
Test script for Felicity Solar API v2.0 with snapshot endpoint
This tests the comprehensive snapshot endpoint for real-time data
"""

import requests
import sys

# Configuration - replace these with your actual values
BASE_URL = "https://shine-api.felicitysolar.com"
USERNAME = "YourUsernameHere"  # Replace with actual username
PASSWORD_HASH = "YourPasswordHashHere"  # Replace with actual password hash
PLANT_ID = "YourPlantIdHere"  # Replace with actual plant ID

# API Endpoints
LOGIN_ENDPOINT = "/v1/base/login/userlogin"
PLANT_LIST_ENDPOINT = "/v1/plant/manager/list_plant"
DEVICE_SNAPSHOT_ENDPOINT = "/v1/device/get_device_snapshot"

def login():
    """Login to get auth token"""
    payload = {
        "username": USERNAME,
        "passwordHash": PASSWORD_HASH,
        "version": "1.0"  # This parameter is required for authentication
    }
    
    print(f"Logging in with payload: {payload}")
    
    try:
        response = requests.post(BASE_URL + LOGIN_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"Login response: {data}")
        
        if data.get("code") == 200:
            token = data["data"]["accessToken"]
            print(f"Login successful! Token: {token[:20]}...")
            return token
        else:
            print(f"Login failed: {data.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"Login error: {e}")
        return None

def get_plant_list(token):
    """Get list of plants and find device serial number"""
    payload = {
        "pageNum": 1,
        "pageSize": 10,
        "plantName": "",
        "deviceSn": "",
        "status": "",
        "isCollected": "",
        "plantType": "",
        "onGridType": "",
        "tagName": "",
        "realName": "",
        "orgCode": "",
        "authorized": "",
        "cityId": "",
        "countryId": "",
        "provinceId": ""
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Getting plant list with payload: {payload}")
    
    try:
        response = requests.post(BASE_URL + PLANT_LIST_ENDPOINT, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"Plant list response: {data}")
        
        if data.get("code") == 200 and data.get("data", {}).get("dataList"):
            for plant in data["data"]["dataList"]:
                if plant["id"] == PLANT_ID:
                    device_list = plant.get("plantDeviceList", [])
                    if device_list:
                        device_sn = device_list[0]["deviceSn"]
                        print(f"Found device serial number: {device_sn}")
                        return device_sn
            print(f"Plant ID {PLANT_ID} not found in plant list")
            return None
        else:
            print(f"Failed to get plant list: {data.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"Plant list error: {e}")
        return None

def get_device_snapshot(token, device_sn):
    """Get comprehensive device snapshot data"""
    from datetime import datetime
    
    payload = {
        "deviceSn": device_sn,
        "deviceType": "OC",  # Default device type
        "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Getting device snapshot with payload: {payload}")
    
    try:
        response = requests.post(BASE_URL + DEVICE_SNAPSHOT_ENDPOINT, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"Device snapshot response code: {data.get('code')}")
        
        if data.get("code") == 200:
            snapshot_data = data.get("data", {})
            
            print("\\n=== DEVICE SNAPSHOT DATA (v2.0) ===")
            print(f"Raw data keys: {list(snapshot_data.keys())}")
            print("\\n--- Power Generation ---")
            print(f"PV Total Power: {snapshot_data.get('pvTotalPower', 'N/A')} W")
            print(f"PV1 Power: {snapshot_data.get('pvPower', 'N/A')} W")
            print(f"PV2 Power: {snapshot_data.get('pv2Power', 'N/A')} W")
            print(f"PV3 Power: {snapshot_data.get('pv3Power', 'N/A')} W")
            print(f"PV4 Power: {snapshot_data.get('pv4Power', 'N/A')} W")
            
            print("\\n--- PV Voltage & Current ---")
            print(f"PV1 Voltage: {snapshot_data.get('pvVolt', 'N/A')} V")
            print(f"PV2 Voltage: {snapshot_data.get('pv2Volt', 'N/A')} V")
            print(f"PV3 Voltage: {snapshot_data.get('pv3Volt', 'N/A')} V")
            print(f"PV1 Current: {snapshot_data.get('pvInCurr', 'N/A')} A")
            print(f"PV2 Current: {snapshot_data.get('pv2InCurr', 'N/A')} A")
            print(f"PV3 Current: {snapshot_data.get('pv3InCurr', 'N/A')} A")
            
            print("\\n--- AC Input (Grid) ---")
            print(f"AC Input Voltage: {snapshot_data.get('acRInVolt', 'N/A')} V")
            print(f"AC Input Current: {snapshot_data.get('acRInCurr', 'N/A')} A")
            print(f"AC Input Frequency: {snapshot_data.get('acRInFreq', 'N/A')} Hz")
            print(f"AC Input Power: {snapshot_data.get('acRInPower', 'N/A')} W")
            
            print("\\n--- AC Output (Load) ---")
            print(f"AC Output Voltage: {snapshot_data.get('acROutVolt', 'N/A')} V")
            print(f"AC Output Current: {snapshot_data.get('acROutCurr', 'N/A')} A")
            print(f"AC Output Frequency: {snapshot_data.get('acROutFreq', 'N/A')} Hz")
            print(f"AC Output Power: {snapshot_data.get('acTotalOutActPower', 'N/A')} W")
            
            print("\\n--- Energy Totals ---")
            print(f"Total Energy: {snapshot_data.get('totalEnergy', 'N/A')} kWh")
            print(f"Today Energy: {snapshot_data.get('ePvToday', 'N/A')} kWh")
            print(f"Grid Feed Today: {snapshot_data.get('eGridFeedToday', 'N/A')} kWh")
            print(f"Grid Feed Total: {snapshot_data.get('eGridFeedTotal', 'N/A')} kWh")
            
            print("\\n--- Temperatures ---")
            print(f"Temperature Max: {snapshot_data.get('tempMax', 'N/A')} °C")
            print(f"Device Temperature Max: {snapshot_data.get('devTempMax', 'N/A')} °C")
            
            print("\\n--- Load & Grid ---")
            print(f"Load Percentage: {snapshot_data.get('loadPercent', 'N/A')} %")
            print(f"Meter Power: {snapshot_data.get('meterPower', 'N/A')} W")
            
            print("\\n--- Device Status ---")
            print(f"Status: {snapshot_data.get('status', 'N/A')}")
            print(f"WiFi Signal: {snapshot_data.get('wifiSignal', 'N/A')} dBm")
            
            print("\\n--- Battery (if present) ---")
            print(f"Battery SOC: {snapshot_data.get('battSoc', 'N/A')} %")
            print(f"Battery Voltage: {snapshot_data.get('battVolt', 'N/A')} V")
            print(f"Battery Current: {snapshot_data.get('battCurr', 'N/A')} A")
            print(f"Battery Power: {snapshot_data.get('bmsPower', 'N/A')} W")
            
            print("\\n=== ALL SNAPSHOT DATA ===")
            for key, value in snapshot_data.items():
                print(f"{key}: {value}")
                
            return True
        else:
            print(f"Failed to get device snapshot: {data.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Device snapshot error: {e}")
        return False

def main():
    """Main test function"""
    print("=== Felicity Solar API v2.0 Test ===")
    print("Testing snapshot endpoint for comprehensive real-time data\\n")
    
    if not all([USERNAME != "YourUsernameHere", PASSWORD_HASH != "YourPasswordHashHere", PLANT_ID != "YourPlantIdHere"]):
        print("ERROR: Please update USERNAME, PASSWORD_HASH, and PLANT_ID in this script")
        sys.exit(1)
    
    # Step 1: Login
    print("Step 1: Login")
    token = login()
    if not token:
        print("Login failed, exiting")
        sys.exit(1)
    
    # Step 2: Get device serial number from plant list
    print("\\nStep 2: Get device serial number")
    device_sn = get_plant_list(token)
    if not device_sn:
        print("Failed to get device serial number, exiting")
        sys.exit(1)
    
    # Step 3: Get comprehensive snapshot data
    print("\\nStep 3: Get device snapshot data")
    success = get_device_snapshot(token, device_sn)
    if not success:
        print("Failed to get device snapshot")
        sys.exit(1)
    
    print("\\n=== Test completed successfully! ===")
    print("The v2.0 snapshot endpoint provides comprehensive real-time data")
    print("including AC input/output, temperatures, battery info, and more!")

if __name__ == "__main__":
    main()