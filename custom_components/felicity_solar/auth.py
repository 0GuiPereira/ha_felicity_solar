"""Authentication manager for Felicity Solar API."""
import logging
import requests
from typing import Optional, Dict, Any

from .const import BASE_URL, LOGIN_ENDPOINT

_LOGGER = logging.getLogger(__name__)

class FelicitySolarAuth:
    """Manages authentication for Felicity Solar API."""
    
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._token: Optional[str] = None
    

    
    def login(self) -> bool:
        """Login and obtain token."""
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
                
                _LOGGER.info("Successfully logged in to Felicity Solar API")
                return True
            else:
                _LOGGER.error(f"Login failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Login error: {e}")
            return False
    

    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid authentication token."""
        # For now, just return the token. In the future, we could add token expiration checking
        # and re-login if needed, but without refresh token functionality
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