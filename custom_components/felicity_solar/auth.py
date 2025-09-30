"""Authentication manager for Felicity Solar API."""
import time
import logging
import requests
from typing import Optional, Dict, Any

from .const import BASE_URL, LOGIN_ENDPOINT, REFRESH_TOKEN_ENDPOINT

_LOGGER = logging.getLogger(__name__)

class FelicitySolarAuth:
    """Manages authentication for Felicity Solar API."""
    
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expire_time: Optional[int] = None
        self._refresh_expire_time: Optional[int] = None
    
    def _is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        if not self._token or not self._token_expire_time:
            return True
        
        # Add 60 second buffer before actual expiration
        current_time = int(time.time() * 1000)
        return current_time >= (self._token_expire_time - 60000)
    
    def _is_refresh_token_expired(self) -> bool:
        """Check if the refresh token is expired."""
        if not self._refresh_token or not self._refresh_expire_time:
            return True
        
        # Add 60 second buffer before actual expiration
        current_time = int(time.time() * 1000)
        return current_time >= (self._refresh_expire_time - 60000)
    
    def login(self) -> bool:
        """Login and obtain tokens."""
        try:
            payload = {
                "userName": self._username,
                "password": self._password,
                "version": "1.0"
            }
            
            response = requests.post(
                BASE_URL + LOGIN_ENDPOINT,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200:
                auth_data = data.get("data", {})
                self._token = auth_data.get("token")
                self._refresh_token = auth_data.get("refreshToken")
                self._token_expire_time = int(auth_data.get("tokenExpireTime", 0))
                self._refresh_expire_time = int(auth_data.get("refTokenExpireTime", 0))
                
                _LOGGER.info("Successfully logged in to Felicity Solar API")
                return True
            else:
                _LOGGER.error(f"Login failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Login error: {e}")
            return False
    
    def refresh_token(self) -> bool:
        """Refresh the authentication token."""
        if not self._refresh_token or self._is_refresh_token_expired():
            _LOGGER.info("Refresh token expired, need to login again")
            return self.login()
        
        try:
            payload = {
                "refreshToken": self._refresh_token
            }
            
            response = requests.post(
                BASE_URL + REFRESH_TOKEN_ENDPOINT,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200:
                auth_data = data.get("data", {})
                self._token = auth_data.get("token")
                self._refresh_token = auth_data.get("refreshToken")
                self._token_expire_time = int(auth_data.get("tokenExpireTime", 0))
                self._refresh_expire_time = int(auth_data.get("refTokenExpireTime", 0))
                
                _LOGGER.info("Successfully refreshed token")
                return True
            elif data.get("code") == 999:
                _LOGGER.info("Need to log in again")
                return self.login()
            else:
                _LOGGER.error(f"Token refresh failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Token refresh error: {e}")
            return False
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid authentication token."""
        if self._is_token_expired():
            if not self.refresh_token():
                return None
        
        return self._token
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        token = self.get_valid_token()
        if not token:
            return {}
        
        return {
            "Authorization": token,
            "Content-Type": "application/json"
        }