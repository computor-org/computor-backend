"""Configuration for support tickets and the team-mailbox bridge.

The API process needs only the team addresses (allowed reply senders) and
whether mail sending is enabled. The IMAP/SMTP credentials are read solely
by the support Temporal worker (queue ``support``), the only container that
can reach the mail host's IMAP listener (computor-infra prod/TEAMMAIL.md).
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORT_TASK_QUEUE = "support"
DEFAULT_TEAM_ADDRESSES = (
    "contact@computor.at abuse@computor.at privacy@computor.at "
    "security@computor.at postmaster@computor.at"
)


def _split(value: Optional[str]) -> List[str]:
    return [p.strip().lower() for p in (value or "").replace(",", " ").split() if p.strip()]


class SupportSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUPPORT_", extra="ignore")

    # The five team addresses: the only permitted reply senders.
    team_addresses: str = DEFAULT_TEAM_ADDRESSES
    # Tickets that involve one of these addresses are visible to _admin only.
    # Empty disables the restriction.
    restricted_addresses: str = "security@computor.at"
    # Display-name suffix of replies: "<Name> via computor.at".
    sender_suffix: str = "via computor.at"
    # Domain used for generated Message-IDs.
    mail_domain: str = "computor.at"

    # Mail bridge (support worker only).
    mail_enabled: bool = False
    mail_poll_seconds: int = Field(120, ge=30)
    imap_host: str = "mail.computor.at"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folders: str = "INBOX Sent"
    sent_folder: str = "Sent"
    smtp_host: str = "mail.computor.at"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Verify the mail host's certificate (off only in throwaway test stacks).
    mail_tls_verify: bool = True
    # Largest attachment stored in the database; bigger ones stay in Dovecot.
    max_attachment_bytes: int = 15 * 1024 * 1024
    # Largest message fetched at all (bigger: headers only + note).
    max_message_bytes: int = 40 * 1024 * 1024

    @property
    def team_address_list(self) -> List[str]:
        return _split(self.team_addresses)

    @property
    def restricted_address_list(self) -> List[str]:
        return _split(self.restricted_addresses)

    @property
    def folder_list(self) -> List[str]:
        return (self.imap_folders or "").split()


@lru_cache
def get_support_settings() -> SupportSettings:
    return SupportSettings()
