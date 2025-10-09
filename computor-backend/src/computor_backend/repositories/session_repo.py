"""Repository for Session management with cache invalidation."""

from typing import Optional, Set
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, or_

from computor_backend.repositories.base import BaseRepository
from computor_backend.model.auth import Session


class SessionRepository(BaseRepository[Session]):
    """Repository for Session with cache invalidation and device tracking."""
    
    def get_entity_tags(self, entity: Session) -> Set[str]:
        """Get cache tags for session invalidation."""
        return {
            f"session:{entity.id}",
            f"session_sid:{entity.sid}",
            f"user_sessions:{entity.user_id}",
            "session:list",
        }
    
    def find_by_session_id_hash(self, session_id_hash: str) -> Optional[Session]:
        """
        Find active session by hashed access token.
        
        Args:
            session_id_hash: SHA-256 hash of access token
            
        Returns:
            Active Session or None
        """
        now = datetime.now(timezone.utc)
        return self.db.query(Session).filter(
            Session.session_id == session_id_hash,
            Session.revoked_at.is_(None),
            Session.ended_at.is_(None),
            or_(
                Session.expires_at.is_(None),
                Session.expires_at > now
            )
        ).first()
    
    def find_by_refresh_token_hash(self, refresh_hash: bytes) -> Optional[Session]:
        """
        Find active session by hashed refresh token.
        
        Args:
            refresh_hash: SHA-256 binary hash of refresh token
            
        Returns:
            Active Session or None
        """
        now = datetime.now(timezone.utc)
        return self.db.query(Session).filter(
            Session.refresh_token_hash == refresh_hash,
            Session.revoked_at.is_(None),
            Session.ended_at.is_(None),
            or_(
                Session.refresh_expires_at.is_(None),
                Session.refresh_expires_at > now
            )
        ).first()
    
    def find_active_sessions_by_user(self, user_id: str | UUID) -> list[Session]:
        """
        Find all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active sessions ordered by last_seen_at desc
        """
        now = datetime.now(timezone.utc)
        return self.db.query(Session).filter(
            Session.user_id == str(user_id),
            Session.revoked_at.is_(None),
            Session.ended_at.is_(None),
            or_(
                Session.expires_at.is_(None),
                Session.expires_at > now
            )
        ).order_by(Session.last_seen_at.desc()).all()
    
    def update_last_seen(
        self,
        session_id: str | UUID,
        ip_address: str
    ) -> Optional[Session]:
        """
        Update last_seen_at and last_ip for activity tracking.
        
        Args:
            session_id: Session ID
            ip_address: Current IP address
            
        Returns:
            Updated Session or None
        """
        updates = {
            "last_seen_at": datetime.now(timezone.utc),
            "last_ip": ip_address
        }
        return self.update(str(session_id), updates)
    
    def increment_refresh_counter(self, session_id: str | UUID) -> Optional[Session]:
        """
        Increment refresh counter when token is refreshed.
        
        Args:
            session_id: Session ID
            
        Returns:
            Updated Session or None
        """
        session = self.get(session_id)
        if session:
            updates = {"refresh_counter": session.refresh_counter + 1}
            return self.update(str(session_id), updates)
        return None
    
    def end_session(
        self,
        session_id: str | UUID,
        reason: Optional[str] = None
    ) -> Optional[Session]:
        """
        Mark session as ended (logout).
        
        Args:
            session_id: Session ID
            reason: Optional reason for ending
            
        Returns:
            Updated Session or None
        """
        now = datetime.now(timezone.utc)
        updates = {
            "ended_at": now,
            "logout_time": now,  # Legacy field
        }
        if reason:
            updates["properties"] = {"end_reason": reason}
        return self.update(str(session_id), updates)
    
    def revoke_session(
        self,
        session_id: str | UUID,
        reason: str = "User initiated"
    ) -> Optional[Session]:
        """
        Revoke a session (security action).
        
        Args:
            session_id: Session ID
            reason: Reason for revocation
            
        Returns:
            Updated Session or None
        """
        now = datetime.now(timezone.utc)
        updates = {
            "revoked_at": now,
            "revocation_reason": reason,
            "ended_at": now,
        }
        return self.update(str(session_id), updates)
    
    def revoke_all_user_sessions(
        self,
        user_id: str | UUID,
        reason: str = "User requested logout from all devices",
        exclude_session_id: Optional[str] = None
    ) -> int:
        """
        Revoke all active sessions for a user.
        
        Args:
            user_id: User ID
            reason: Reason for mass revocation
            exclude_session_id: Optional session ID to exclude (current session)
            
        Returns:
            Count of revoked sessions
        """
        sessions = self.find_active_sessions_by_user(user_id)
        count = 0
        for session in sessions:
            if exclude_session_id and str(session.id) == str(exclude_session_id):
                continue
            self.revoke_session(str(session.id), reason)
            count += 1
        return count
    
    def cleanup_expired_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old ended/revoked sessions.
        
        Args:
            days_old: Delete sessions older than this many days
            
        Returns:
            Count of deleted sessions
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        # Find old ended or revoked sessions
        old_sessions = self.db.query(Session).filter(
            or_(
                and_(Session.ended_at.isnot(None), Session.ended_at < cutoff),
                and_(Session.revoked_at.isnot(None), Session.revoked_at < cutoff)
            )
        ).all()
        
        count = 0
        for session in old_sessions:
            self.delete(str(session.id))
            count += 1
        
        return count
