"""Authentication manager for Felicity Solar API."""
from __future__ import annotations

import logging
from typing import Optional, Dict
import requests

from .const import BASE_URL, LOGIN_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class FelicitySolarAuth:
    """Manages authentication for Felicity Solar API."""

    def __init__(self, username: str, password_hash: str) -> None:
        # A API desta integração espera a password já em hash (como tens no teu flow)
        self._username = username
        self._password_hash = password_hash
        self._token: Optional[str] = None

    def login(self) -> bool:
        """Perform login and store token."""
        try:
            payload = {
                "username": self._username,
                "password": self._password_hash,
                "userType": 1,
            }
            _LOGGER.debug("Login payload: %s", payload)

            r = requests.post(
                BASE_URL + LOGIN_ENDPOINT,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            _LOGGER.debug("Login response: %s", data)

            if data.get("code") != 200:
                _LOGGER.error("Login failed: %s", data.get("message"))
                return False

            token = (data.get("data") or {}).get("token")
            if not token:
                _LOGGER.error("Login ok mas sem token")
                return False

            # Normalizar prefixo Bearer_
            if not token.startswith("Bearer_"):
                token = f"Bearer_{token}"

            self._token = token
            _LOGGER.info("Login Felicity Solar: OK")
            return True

        except Exception as exc:
            _LOGGER.exception("Erro no login: %s", exc)
            return False

    # --- helpers
    def get_valid_token(self) -> Optional[str]:
        return self._token

    def get_auth_headers(self) -> Dict[str, str]:
        """Return HTTP headers com Authorization."""
        if not self._token:
            return {}
        return {
            "Authorization": self._token,
            "Content-Type": "application/json",
        }
