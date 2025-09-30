#!/usr/bin/env python3
"""
Test script for Felicity Solar API endpoints.
This script tests the API calls without Home Assistant to verify they work correctly.
"""

import requests
import json
from datetime import datetime
import getpass

BASE_URL = "https://shine-api.felicitysolar.com"
LOGIN_ENDPOINT = "/userlogin"
DEVICE_ENDPOINT = "/device/get_device_realtime_icon_template_info"
PLANT_LIST_ENDPOINT = "/plant/list_plant"
PLANT_DETAILS_ENDPOINT = "/plant/plantDetails"
DATAENERGY_ENDPOINT = "/openApi/data/deviceDataEnergy"

def login(email, password):
    """Login to Felicity Solar API."""
    print("Attempting login...")
    payload = {"userName": email, "password": password, "version": "1.0"}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(BASE_URL + LOGIN_ENDPOINT, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            token = data["data"]["token"]
            print("Login OK, token prefix:", token[:24], "...")
            return token
        else:
            print(f"Login failed: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def get_device_info(token):
    """Get device realtime information."""
    print("\\nTesting device realtime endpoint...")
    url = BASE_URL + DEVICE_ENDPOINT
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "deviceSn": None,
        "icons": ["BLOCK_PV"],
        "plantId": "11114725281235393",
        "pageSize": 10,
        "pageNum": 1,
        "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        print(f"Device info response code: {data.get('code')}")
        print(f"Device info message: {data.get('message')}")
        
        if data.get("code") == 200 and data.get("data", {}).get("dataList"):
            device = data["data"]["dataList"][0]
            print(f"Device SN: {device.get('deviceSn')}")
            print(f"Device Type: {device.get('deviceType')}")
            print(f"Device Model: {device.get('deviceModel')}")
            print(f"Status: {device.get('status')}")
            
            # Parse PV data if available
            if "templateBlockVO" in device and "tables" in device["templateBlockVO"]:
                tables = device["templateBlockVO"]["tables"]
                if tables:
                    # First table - PV strings data
                    table1 = tables[0]
                    print(f"\\nPV Strings Data:")
                    headers = table1.get("horizontalHeader", [])
                    string_names = table1.get("tableVerticalHeader", [])
                    points = table1.get("points", [])
                    
                    for i, string_name in enumerate(string_names):
                        if i < len(points):
                            string_data = points[i]
                            print(f"{string_name}: ", end="")
                            for j, header in enumerate(headers):
                                if j < len(string_data):
                                    clean_header = header.replace("\\n", " ")
                                    print(f"{clean_header}: {string_data[j]}", end=" | ")
                            print()
                    
                    # Second table - Total PV power
                    if len(tables) > 1:
                        table2 = tables[1]
                        total_points = table2.get("points", [])
                        if total_points and total_points[0]:
                            print(f"\\nTotal PV Power: {total_points[0][0]} W")
        
        return data
    except Exception as e:
        print(f"Device info error: {e}")
        return None

def get_plant_details(token):
    """Get detailed plant information."""
    print("\\nTesting plant details endpoint...")
    url = BASE_URL + PLANT_DETAILS_ENDPOINT
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "plantId": "11114725281235393",
        "currentDateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        print(f"Plant details response code: {data.get('code')}")
        print(f"Plant details message: {data.get('message')}")
        
        if data.get("code") == 200:
            plant_data = data.get("data", {})
            print(f"Plant details: {json.dumps(plant_data, indent=2)}")
        
        return data
    except Exception as e:
        print(f"Plant details error: {e}")
        return None

def list_plants(token):
    """List all plants."""
    print("\\nTesting plant list endpoint...")
    url = BASE_URL + PLANT_LIST_ENDPOINT
    headers = {"Authorization": token, "Content-Type": "application/json"}
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

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        print(f"Plant list response code: {data.get('code')}")
        print(f"Plant list message: {data.get('message')}")
        
        if data.get("code") == 200 and data.get("data", {}).get("dataList"):
            plants = data["data"]["dataList"]
            for plant in plants:
                print(f"Plant ID: {plant.get('id')}")
                print(f"Plant Name: {plant.get('plantName')}")
                print(f"Current Power: {plant.get('currentPower')} {plant.get('currentPowerUnit')}")
                print(f"Today Energy: {plant.get('todayEnergy')} {plant.get('todayEnergyUnit')}")
                print(f"Total Energy: {plant.get('totalEnergy')} {plant.get('totalEnergyUnit')}")
                print("-" * 30)
        
        return data
    except Exception as e:
        print(f"Plant list error: {e}")
        return None

def main():
    """Main function to test all endpoints."""
    print("Felicity Solar API Test")
    print("=" * 50)
    
    # Get credentials from user input
    print("Enter your Felicity Solar credentials:")
    email = input("Email: ")
    password_hash = getpass.getpass("Password Hash (hidden): ")
    
    if not email or not password_hash:
        print("Both email and password hash are required!")
        return
    
    # Login
    token = login(email, password_hash)
    if not token:
        print("Login failed, cannot proceed with tests")
        return
    
    # Test all endpoints
    print("\\n" + "=" * 50)
    plants = list_plants(token)
    
    print("\\n" + "=" * 50)
    plant_details = get_plant_details(token)
    
    print("\\n" + "=" * 50)
    device_info = get_device_info(token)
    
    print("\\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    main()