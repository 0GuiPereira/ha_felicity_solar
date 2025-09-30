#!/usr/bin/env python3
"""
Simple test with hardcoded credentials for quick testing.
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://shine-api.felicitysolar.com"
LOGIN_ENDPOINT = "/userlogin"
DEVICE_ENDPOINT = "/device/get_device_realtime_icon_template_info"
PLANT_LIST_ENDPOINT = "/plant/list_plant"
PLANT_DETAILS_ENDPOINT = "/plant/plantDetails"

# Your credentials (you can change these)
EMAIL = "piscinas_minueto0n@icloud.com"
PASSWORD = "Rkut+k7bEfHXVymtKLpsVvyXvmh4iPIxpytfA18JL3+IO2H1LScDg/e+ptqCyDGCHmHhb1RTVJgrtgGxuiG036RuGcxxzFMOYf1O0Kz5IKSH98jjOynN72K3LMKw68iiY/kBDKxa6Laed3+sQGbYI11JMdL3BzvzHKvamMjao5oEYvsEX30IQ7Vbip2f1FDhq3Dcoa84YnoqVAfSDFke9wrPF9xgGVpF2EUiAKNxk79QBt5eHkd2RM4ExyZ8gXfJ/QCH+XVWgcfaJwoYRjM3xF430f1jNVW6/R38GXxYEXPKZoFGGL6a/WRHd7KYsNAJlh6362jNJHEIpJuBRExvSw=="

def login():
    """Login to get token."""
    print("Logging in...")
    payload = {"userName": EMAIL, "password": PASSWORD, "version": "1.0"}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(BASE_URL + LOGIN_ENDPOINT, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    
    print(f"Login response: {data}")
    
    if data.get("code") == 200:
        token = data["data"]["token"]
        print(f"Login successful! Token: {token[:30]}...")
        return token
    else:
        print(f"Login failed: {data}")
        return None

def test_plants(token):
    """Test plant list endpoint."""
    print("\\nTesting plant list...")
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

    response = requests.post(BASE_URL + PLANT_LIST_ENDPOINT, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    
    print(f"Plant list response: {json.dumps(data, indent=2)}")
    return data

def test_device_info(token):
    """Test device info endpoint."""
    print("\\nTesting device info...")
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {
        "deviceSn": None,
        "icons": ["BLOCK_PV"],
        "plantId": "11114725281235393",
        "pageSize": 10,
        "pageNum": 1,
        "dateStr": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    response = requests.post(BASE_URL + DEVICE_ENDPOINT, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    
    print(f"Device info response: {json.dumps(data, indent=2)}")
    return data

if __name__ == "__main__":
    try:
        token = login()
        if token:
            test_plants(token)
            test_device_info(token)
        else:
            print("Failed to get token")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()