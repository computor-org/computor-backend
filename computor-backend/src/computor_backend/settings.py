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
        # Env var is KEYCLOAK_ENABLED (same name used by the template, compose, and computor.sh).
        self.ENABLE_KEYCLOAK = os.environ.get("KEYCLOAK_ENABLED", "true").lower() in ["true", "1", "yes", "on"]
        self.AUTH_PLUGINS_CONFIG = os.environ.get("AUTH_PLUGINS_CONFIG", None)  # Path to plugin config file

        # Bootstrap admin: provisioned in Keycloak on startup (email is the username).
        self.API_ADMIN_EMAIL = os.environ.get("API_ADMIN_EMAIL", None)
        self.API_ADMIN_PASSWORD = os.environ.get("API_ADMIN_PASSWORD", None)

        # GDPR consent gate (middleware/consent.py). The gate is additionally
        # inactive while no policy_versions row is effective, so this flag is
        # an operational escape hatch, not the primary rollout switch.
        self.CONSENT_GATE_ENABLED = os.environ.get("CONSENT_GATE_ENABLED", "true").lower() in ["true", "1", "yes", "on"]

        # Extension public download URL
        self.EXTENSION_PUBLIC_DOWNLOAD_URL = os.environ.get("EXTENSION_PUBLIC_DOWNLOAD_URL", None)

        # Public base URL of the whole deployment (full URL incl. scheme, e.g.
        # https://computor.example.org). The web app is served at its root, the
        # API at $PUBLIC_DOMAIN/api, etc. Primary source for the web app URL
        # surfaced by GET /instance-info (so clients like the VSCode extension
        # can deep-link users to the consent page).
        self.PUBLIC_DOMAIN = os.environ.get("PUBLIC_DOMAIN", None)

        # Optional override for the web app URL when it is NOT at the root of
        # PUBLIC_DOMAIN (split deployment) or in dev (PUBLIC_DOMAIN empty, web on
        # localhost:3000). When unset, /instance-info uses PUBLIC_DOMAIN.
        self.WEB_APP_URL = os.environ.get("WEB_APP_URL", None)

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
