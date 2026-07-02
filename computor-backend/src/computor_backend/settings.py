import os
import threading

class BackendSettings:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.DEBUG_MODE = os.environ.get("DEBUG_MODE","development")
        self.API_LOCAL_STORAGE_DIR = os.environ.get("API_LOCAL_STORAGE_DIR",None)

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
        self.WS_SEND_TIMEOUT = int(os.environ.get("WS_SEND_TIMEOUT", "10"))  # seconds for send operations

        self.ANALYTICS_ROOT = os.environ.get(
            "ANALYTICS_ROOT",
            "/srv/computor/analytics",
        )
        self.ANALYTICS_SOURCE_NAME = os.environ.get(
            "ANALYTICS_SOURCE_NAME",
            "green",
        )
        # Analytics snapshots are taken from THIS system's own backend postgres.
        # (In release/2026.10 the analytics instance ran on a separate machine and
        # pulled from another machine's postgres over an SSH tunnel; here the source
        # IS the backend's own database.) So the snapshot source defaults to the
        # backend's own connection — no separate source config or tunnel needed. An
        # explicit ANALYTICS_SOURCE_DATABASE_URL still overrides (e.g. a dedicated
        # read-only role). The refresh always runs in a read-only transaction
        # (default_transaction_read_only=on + BEGIN READ ONLY) regardless of the
        # account it connects with, so reusing the backend role cannot write.
        _pg_user = os.environ.get("POSTGRES_USER")
        _pg_password = os.environ.get("POSTGRES_PASSWORD")
        _pg_host = os.environ.get("POSTGRES_HOST", "localhost")
        _pg_port = os.environ.get("POSTGRES_PORT", "5432")
        _pg_db = os.environ.get("POSTGRES_DB")
        _backend_postgres_url = (
            f"postgresql+psycopg2://{_pg_user}:{_pg_password}@{_pg_host}:{_pg_port}/{_pg_db}"
            if _pg_user and _pg_db
            else None
        )
        # `or` (not a plain default) so an empty override — which compose passes
        # as "" when the .env var is unset — still falls back to the local DB.
        self.ANALYTICS_SOURCE_DATABASE_URL = (
            os.environ.get("ANALYTICS_SOURCE_DATABASE_URL") or _backend_postgres_url
        )
        self.ANALYTICS_EXPORT_CHUNK_SIZE = int(
            os.environ.get("ANALYTICS_EXPORT_CHUNK_SIZE", "100000")
        )
        # Read-only access to the source instance's API, used to fetch an
        # example's source files live when a lecturer opens it. The browser
        # never calls the source directly; this analytics backend does, server
        # side. Empty token leaves the source view gracefully unavailable.
        self.ANALYTICS_SOURCE_API_URL = os.environ.get(
            "ANALYTICS_SOURCE_API_URL",
            None,
        )
        self.ANALYTICS_SOURCE_API_TOKEN = os.environ.get(
            "ANALYTICS_SOURCE_API_TOKEN",
            None,
        )

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BackendSettings, cls).__new__(cls)
        return cls._instance

settings = BackendSettings()