"""Repositories for GDPR consent records and policy versions."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from computor_backend.model.consent import PolicyVersion, UserConsent
from computor_backend.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PolicyVersionRepository(BaseRepository[PolicyVersion]):
    """Append-only repository for policy versions. No update/delete methods on purpose."""

    def __init__(self, db: Session, cache=None):
        super().__init__(db, PolicyVersion, cache)

    def get_current(self) -> Optional[PolicyVersion]:
        """The version in effect now: latest effective_from <= now()."""
        return (
            self.db.query(PolicyVersion)
            .filter(PolicyVersion.effective_from <= func.now())
            .order_by(PolicyVersion.effective_from.desc())
            .first()
        )

    def get_by_version(self, version: str) -> Optional[PolicyVersion]:
        return self.db.query(PolicyVersion).filter(PolicyVersion.version == version).first()

    def list_versions(self) -> List[PolicyVersion]:
        return self.db.query(PolicyVersion).order_by(PolicyVersion.effective_from.desc()).all()


class ConsentRepository(BaseRepository[UserConsent]):
    def __init__(self, db: Session, cache=None):
        super().__init__(db, UserConsent, cache)

    def get_active_consent(self, user_id: str, policy_version: str) -> Optional[UserConsent]:
        """Active (non-withdrawn) consent of a user for a specific policy version."""
        return (
            self.db.query(UserConsent)
            .filter(
                UserConsent.user_id == user_id,
                UserConsent.policy_version == policy_version,
                UserConsent.withdrawn_at.is_(None),
            )
            .first()
        )

    def create_consent(
        self,
        user_id: str,
        policy_version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        purposes: Optional[dict] = None,
    ) -> UserConsent:
        """Record consent. Idempotent: a concurrent duplicate insert hits the
        partial unique index and resolves to the already-existing active row."""
        consent = UserConsent(
            user_id=user_id,
            policy_version=policy_version,
            ip_address=ip_address,
            user_agent=user_agent,
            purposes=purposes,
        )
        self.db.add(consent)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_active_consent(user_id, policy_version)
            if existing is not None:
                return existing
            raise
        self.db.refresh(consent)
        return consent

    def withdraw(self, user_id: str) -> int:
        """Withdraw ALL active consents of a user (GDPR Art. 7(3)).

        Returns the number of rows withdrawn. Rows are kept (withdrawn_at set)
        for the audit trail.
        """
        count = (
            self.db.query(UserConsent)
            .filter(UserConsent.user_id == user_id, UserConsent.withdrawn_at.is_(None))
            .update(
                {UserConsent.withdrawn_at: datetime.now(timezone.utc)},
                synchronize_session=False,
            )
        )
        self.db.commit()
        return count
