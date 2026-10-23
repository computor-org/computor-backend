"""Configuration for support tickets and the team-mailbox bridge.

The API process needs only the team addresses (allowed reply senders) and
whether mail sending is enabled. The IMAP/SMTP credentials are read solely
by the support Temporal worker (queue ``support``), the only container that
can reach the mail host's IMAP listener (computor-infra prod/TEAMMAIL.md).
"""
from functools import lru_cache
from typing import List, Literal, Optional

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

    # Where "Report a Problem" goes (issues#520 step 2): ``tickets`` files a
    # support ticket (the default), ``github`` keeps the older direct GitHub
    # issue path, ``off`` hides the entry point. Clients read it from
    # ``GET /instance-info`` (``issue_reporting.mode``).
    report_mode: Literal["tickets", "github", "off"] = "tickets"
    # Largest log file a reporter may attach to a problem report.
    report_max_log_bytes: int = Field(1024 * 1024, ge=0)

    # Mail bridge (support worker only).
    mail_enabled: bool = False
    # Welcome-only workers need SMTP without periodic IMAP mailbox imports.
    mail_import_enabled: bool = True
    mail_poll_seconds: int = Field(120, ge=30)
    imap_host: str = "mail.computor.at"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folders: str = "INBOX Sent"
    sent_folder: str = "Sent"
    smtp_host: str = "mail.computor.at"
    smtp_port: int = 587
    # Disable only for an explicitly configured local test relay such as Mailpit.
    smtp_starttls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    # Verify the mail host's certificate (off only in throwaway test stacks).
    mail_tls_verify: bool = True
    # Welcome mail after a completed registration (issues#185). Needs the mail
    # bridge (``mail_enabled``) on the support worker. The API only queues the
    # mail when this flag is on as well, so a deployment without the support
    # worker never accumulates queued workflows.
    welcome_mail_enabled: bool = False
    welcome_from: str = "contact@computor.at"
    # Public address of the web UI, linked in the welcome mail.
    site_url: str = "https://computor.at"
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
