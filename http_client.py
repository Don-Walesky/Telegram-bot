"""
HTTP Client Provider & Connection Pooling Service
Provides reusable, thread-safe httpx.Client sessions for LiveScore, SportyBet,
and code conversion API integrations with TCP connection pooling and automatic cleanup.
"""

import logging
from typing import Dict, Optional
import httpx
from config import config

logger = logging.getLogger(__name__)


class HTTPClientProvider:
    _clients: Dict[float, httpx.Client] = {}

    @classmethod
    def get_client(cls, timeout: Optional[float] = None) -> httpx.Client:
        """
        Returns a shared httpx.Client instance for the specified timeout.
        Re-uses existing connection pools across requests to eliminate per-request setup overhead.
        """
        effective_timeout = timeout if timeout is not None else config.services.livescore_timeout
        if effective_timeout not in cls._clients or cls._clients[effective_timeout].is_closed:
            cls._clients[effective_timeout] = httpx.Client(
                timeout=effective_timeout,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return cls._clients[effective_timeout]

    @classmethod
    def close_all(cls) -> None:
        """Closes all active pooled HTTP client sessions cleanly."""
        for timeout_val, client in list(cls._clients.items()):
            try:
                if not client.is_closed:
                    client.close()
            except Exception as e:
                logger.warning(f"Error closing HTTP client session (timeout {timeout_val}s): {e}")
        cls._clients.clear()
