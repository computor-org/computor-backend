import os
import threading

class BackendSettings:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.DEBUG_MODE = os.environ.get("DEBUG_MODE","development")

        # Documents API: write side maintained by ``api/documents.py``,
        # read side served by the ``static-server`` container at /docs.
        # Both must point at the same host directory; see DOCUMENTS_LEGACY.md
        # and the compose mounts.
        self.DOCUMENTS_ROOT = os.environ.get("DOCUMENTS_ROOT", None)
        self.DOCUMENTS_MAX_FILE_SIZE = int(os.environ.get("DOCUMENTS_MAX_FILE_SIZE", str(10 * 1024 * 1024)))

        # Security: Force disable debug info in API responses (overrides DEBUG_MODE)
        # Set DISABLE_API_DEBUG_INFO=true to hide sensitive information even in development
        self.DISABLE_API_DEBUG_INFO = os.environ.get("DISABLE_API_DEBUG_INFO", "false").lower() in ["true", "1", "yes", "on"]

        # Authentication settings
        # Env var is KEYCLOAK_ENABLED (same name used by the template, compose, and startup.sh).
        self.ENABLE_KEYCLOAK = os.environ.get("KEYCLOAK_ENABLED", "true").lower() in ["true", "1", "yes", "on"]
        self.AUTH_PLUGINS_CONFIG = os.environ.get("AUTH_PLUGINS_CONFIG", None)  # Path to plugin config file

        # Bootstrap admin: provisioned in Keycloak on startup (email is the username).
        self.API_ADMIN_EMAIL = os.environ.get("API_ADMIN_EMAIL", None)
        self.API_ADMIN_PASSWORD = os.environ.get("API_ADMIN_PASSWORD", None)

        # Extension public download URL
        self.EXTENSION_PUBLIC_DOWNLOAD_URL = os.environ.get("EXTENSION_PUBLIC_DOWNLOAD_URL", None)

        # WebSocket settings
        self.WS_MAX_CONNECTIONS_PER_USER = int(os.environ.get("WS_MAX_CONNECTIONS_PER_USER", "10"))
        self.WS_MAX_TOTAL_CONNECTIONS = int(os.environ.get("WS_MAX_TOTAL_CONNECTIONS", "10000"))
        self.WS_PRESENCE_TTL = int(os.environ.get("WS_PRESENCE_TTL", "60"))  # seconds
        self.WS_TYPING_TTL = int(os.environ.get("WS_TYPING_TTL", "5"))  # seconds
        self.WS_HANDLER_TIMEOUT = int(os.environ.get("WS_HANDLER_TIMEOUT", "5"))  # seconds per handler
        self.WS_PING_INTERVAL = int(os.environ.get("WS_PING_INTERVAL", "25"))  # client-side ping interval
        self.WS_SEND_TIMEOUT = int(os.environ.get("WS_SEND_TIMEOUT", "10"))  # seconds for send operations

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BackendSettings, cls).__new__(cls)
        return cls._instance

settings = BackendSettings()