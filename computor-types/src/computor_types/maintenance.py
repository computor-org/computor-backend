"""
Maintenance mode DTOs.

Pydantic models for maintenance status, activation, and scheduling.
"""

import json
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator

# Built-in texts in both reading languages; every event and the status carry
# the pair as ``message_i18n`` so each client picks its reader's language.
DEFAULT_TEXTS: Dict[str, Dict[str, str]] = {
    "activated": {
        "de": "Das System wird gerade planmäßig gewartet.",
        "en": "The system is undergoing scheduled maintenance.",
    },
    "scheduled": {
        "de": "Eine Wartung ist geplant.",
        "en": "Scheduled maintenance is planned.",
    },
    "reminder": {
        "de": "Die geplante Wartung steht bevor.",
        "en": "Scheduled maintenance is approaching.",
    },
    "update_reminder": {
        "de": "Das System startet für ein geplantes Update neu.",
        "en": "The system will restart for a scheduled update.",
    },
    "deactivated": {
        "de": "Die Wartung ist abgeschlossen. Alle Funktionen stehen wieder zur Verfügung.",
        "en": "Maintenance complete. Full service has been restored.",
    },
    "cancelled": {
        "de": "Die geplante Wartung wurde abgesagt.",
        "en": "Scheduled maintenance has been cancelled.",
    },
}

MESSAGE_I18N_DESCRIPTION = (
    "The message in German and English ({'de': ..., 'en': ...}); clients show "
    "the reader's language and fall back to `message`"
)


def _clean_i18n(value: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Keep the non-blank de/en entries; an empty map means no translation."""
    if value is None:
        return None
    cleaned = {
        lang: text.strip()
        for lang, text in value.items()
        if lang in ("de", "en") and isinstance(text, str) and text.strip()
    }
    return cleaned or None


def stored_message_i18n(raw: Optional[str]) -> Optional[Dict[str, str]]:
    """The pair as kept in Redis (JSON); anything unreadable counts as absent."""
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return _clean_i18n(value) if isinstance(value, dict) else None


class MaintenanceStatusGet(BaseModel):
    """Current maintenance status."""
    active: bool = False
    message: str = ""
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
    activated_by_name: Optional[str] = None
    scheduled_at: Optional[str] = None
    scheduled_by: Optional[str] = None
    scheduled_by_name: Optional[str] = None
    message_i18n: Optional[Dict[str, str]] = Field(
        default=None, description=MESSAGE_I18N_DESCRIPTION
    )


class _MessageI18n(BaseModel):
    @field_validator("message_i18n", mode="after", check_fields=False)
    @classmethod
    def _only_de_en(cls, value):
        return _clean_i18n(value)


class MaintenanceActivate(_MessageI18n):
    """Activate maintenance mode."""
    message: str = Field(
        default=DEFAULT_TEXTS["activated"]["en"],
        description="Message shown to users",
    )
    message_i18n: Optional[Dict[str, str]] = Field(
        default=None, description=MESSAGE_I18N_DESCRIPTION
    )
    notify_websocket: bool = Field(
        default=True,
        description="Broadcast maintenance notification via WebSocket",
    )


class MaintenanceSchedule(_MessageI18n):
    """Schedule future maintenance."""
    scheduled_at: str = Field(
        ..., description="ISO8601 datetime when maintenance will start"
    )
    message: str = Field(
        default=DEFAULT_TEXTS["scheduled"]["en"],
        description="Message shown to users",
    )
    message_i18n: Optional[Dict[str, str]] = Field(
        default=None, description=MESSAGE_I18N_DESCRIPTION
    )
    notify_websocket: bool = Field(
        default=True,
        description="Broadcast schedule notification via WebSocket",
    )
