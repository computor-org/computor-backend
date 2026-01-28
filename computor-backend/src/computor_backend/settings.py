import os
import threading

class BackendSettings:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.DEBUG_MODE = os.environ.get("DEBUG_MODE","development")
        self.API_LOCAL_STORAGE_DIR = os.environ.get("API_LOCAL_STORAGE_DIR",None)

        # Security: Force disable debug info in API responses (overrides DEBUG_MODE)
        # Set DISABLE_API_DEBUG_INFO=true to hide sensitive information even in development
        self.DISABLE_API_DEBUG_INFO = os.environ.get("DISABLE_API_DEBUG_INFO", "false").lower() in ["true", "1", "yes", "on"]

        # Authentication settings
        self.ENABLE_KEYCLOAK = os.environ.get("ENABLE_KEYCLOAK", "true").lower() in ["true", "1", "yes", "on"]
        self.AUTH_PLUGINS_CONFIG = os.environ.get("AUTH_PLUGINS_CONFIG", None)  # Path to plugin config file

        # Extension public download URL
        self.EXTENSION_PUBLIC_DOWNLOAD_URL = os.environ.get("EXTENSION_PUBLIC_DOWNLOAD_URL", None)

        # WebSocket settings
        self.WS_MAX_CONNECTIONS_PER_USER = int(os.environ.get("WS_MAX_CONNECTIONS_PER_USER", "10"))
        self.WS_MAX_TOTAL_CONNECTIONS = int(os.environ.get("WS_MAX_TOTAL_CONNECTIONS", "10000"))
        self.WS_PRESENCE_TTL = int(os.environ.get("WS_PRESENCE_TTL", "60"))  # seconds
        self.WS_TYPING_TTL = int(os.environ.get("WS_TYPING_TTL", "5"))  # seconds
        self.WS_HANDLER_TIMEOUT = int(os.environ.get("WS_HANDLER_TIMEOUT", "5"))  # seconds per handler
        self.WS_PING_INTERVAL = int(os.environ.get("WS_PING_INTERVAL", "25"))  # client-side ping interval
        self.WS_SEND_TIMEOUT = int(os.environ.get("WS_SEND_TIMEOUT", "2"))  # seconds for send operations

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BackendSettings, cls).__new__(cls)
        return cls._instance

settings = BackendSettings()