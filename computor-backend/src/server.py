import asyncio
import os
import logging
import sys
import uvicorn
from computor_backend.settings import settings
from computor_backend.server import startup_logic


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log output."""

    # ANSI color codes
    grey = "\x1b[38;21m"
    blue = "\x1b[34m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    orange = "\x1b[38;5;208m"  # Orange color for timestamp
    reset = "\x1b[0m"

    COLORS = {
        logging.DEBUG: grey,
        logging.INFO: green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red
    }

    def format(self, record):
        # Format the record first (this creates the formatted string with asctime)
        formatted = super().format(record)

        # Only colorize if outputting to terminal
        if sys.stdout.isatty():
            log_color = self.COLORS.get(record.levelno, self.grey)

            # Parse the formatted string and apply colors
            # Format is: "timestamp - LEVEL - name - message"
            parts = formatted.split(' - ', 3)
            if len(parts) >= 3:
                timestamp = parts[0]
                level = parts[1]
                rest = ' - '.join(parts[2:])

                # Apply colors (orange for timestamp instead of grey)
                colored_timestamp = f"{self.orange}{timestamp}{self.reset}"
                colored_level = f"{log_color}{level}{self.reset}"
                formatted = f"{colored_timestamp} - {colored_level} - {rest}"

        return formatted


# Setup logging with colors and datetime
def setup_logging():
    """Configure logging with colors and datetime."""
    # Remove existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    # Create formatter with colors
    formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)-8s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Set handler to root logger
    root.addHandler(handler)
    root.setLevel(logging.WARNING)  # Default to WARNING to avoid verbose logs

    # Configure uvicorn.access to use our formatter
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = []  # Remove default handlers
    access_logger.addHandler(handler)  # Use our handler with colors
    access_logger.setLevel(logging.INFO)  # Keep access logs at INFO

    # Configure uvicorn.error to use our formatter
    error_logger = logging.getLogger("uvicorn.error")
    error_logger.handlers = []
    error_logger.addHandler(handler)
    error_logger.setLevel(logging.INFO)


# Configure logging
setup_logging()

# Configure logging levels for modules based on environment
def configure_module_logging():
    """Configure module logging based on environment variables."""

    # Get log level from environment (default to WARNING for quiet operation)
    ws_log_level = os.environ.get("WEBSOCKET_LOG_LEVEL", "WARNING").upper()

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if ws_log_level not in valid_levels:
        ws_log_level = "WARNING"

    # Configure all WebSocket-related loggers
    websocket_modules = [
        "computor_backend.websocket",
        "computor_backend.websocket.router",
        "computor_backend.websocket.connection_manager",
        "computor_backend.websocket.pubsub",
        "computor_backend.websocket.handlers",
        "computor_backend.websocket.auth",
        "computor_backend.websocket.broadcast",
    ]

    for module in websocket_modules:
        logger = logging.getLogger(module)
        logger.setLevel(getattr(logging, ws_log_level))

    # Set all computor_backend modules to WARNING to avoid verbose logs
    # Add the root module and all sub-modules
    backend_modules = [
        "computor_backend",  # Root module - this catches all sub-modules
        "computor_backend.api",
        "computor_backend.repositories",
        "computor_backend.business_logic",
        "computor_backend.services",
        "computor_backend.tasks",
        "computor_backend.auth",
        "computor_backend.database",
        "computor_backend.minio_client",
    ]

    for module in backend_modules:
        logger = logging.getLogger(module)
        logger.setLevel(logging.WARNING)  # Only warnings and errors

    # Also configure uvicorn access logs based on environment
    if ws_log_level in ["ERROR", "CRITICAL"]:
        # Suppress access logs in quiet mode
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return ws_log_level

if __name__ == "__main__":
    # Configure module logging
    ws_level = configure_module_logging()

    # Get Uvicorn log level from environment or use default
    # Default to "info" to always show HTTP requests unless explicitly set otherwise
    uvicorn_log_level = os.environ.get("UVICORN_LOG_LEVEL", "info").lower()

    # Note: We intentionally DON'T map WebSocket level to Uvicorn level
    # This allows us to have quiet WebSocket logs but still see HTTP requests

    print(f"Starting server with WebSocket log level: {ws_level}, Uvicorn log level: {uvicorn_log_level}")

    if settings.DEBUG_MODE != "production":
        asyncio.run(startup_logic())

    # Create custom uvicorn log config to use our formatter
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "colored": {
                "()": ColoredFormatter,
                "fmt": "%(asctime)s - %(levelname)-8s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "access": {
                "()": ColoredFormatter,
                "fmt": "%(asctime)s - %(levelname)-8s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "colored",
                "stream": "ext://sys.stdout"
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "access",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": uvicorn_log_level.upper(),
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": uvicorn_log_level.upper(),
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO" if uvicorn_log_level != "error" else "WARNING",
                "propagate": False
            }
        }
    }

    uvicorn.run(
        "computor_backend.server:app",
        host="0.0.0.0",
        port=8000,
        log_config=log_config,  # Use our custom log config
        reload=True,
        workers=1
    )