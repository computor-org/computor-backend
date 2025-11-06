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

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BackendSettings, cls).__new__(cls)
        return cls._instance

settings = BackendSettings()