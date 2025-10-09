from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime,
    Enum, ForeignKey, Index, Integer, LargeBinary, String, text
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = 'user'
    __table_args__ = (
        CheckConstraint(
            "(user_type <> 'token') OR (token_expiration IS NOT NULL)",
            name='ck_user_token_expiration'
        ),
    )

    number = Column(String(255), unique=True)
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)
    archived_at = Column(DateTime(True))
    given_name = Column(String(255))
    family_name = Column(String(255))
    email = Column(String(320), unique=True)
    user_type = Column(Enum('user', 'token', name='user_type'), nullable=False, server_default=text("'user'::user_type"))
    fs_number = Column(BigInteger, nullable=False, server_default=text("nextval('user_unique_fs_number_seq'::regclass)"))
    token_expiration = Column(DateTime(True))
    username = Column(String(255), unique=True)
    password = Column(String(255))
    auth_token = Column(String(4096))  # Added from PostgreSQL migrations

    # Relationships
    course_members = relationship("CourseMember", foreign_keys="CourseMember.user_id", back_populates="user", uselist=True, lazy="select")
    student_profiles = relationship("StudentProfile", foreign_keys="StudentProfile.user_id", back_populates="user", uselist=True, lazy="select")
    accounts = relationship("Account", back_populates="user", uselist=True, lazy="select")
    sessions = relationship("Session", back_populates="user", uselist=True, lazy="select")
    profile = relationship("Profile", back_populates="user", uselist=False, lazy="select")
    user_groups = relationship("UserGroup", back_populates="user", uselist=True, lazy="select")
    user_roles = relationship("UserRole", back_populates="user", uselist=True, lazy="select")
    organization = relationship("Organization", foreign_keys="Organization.user_id", uselist=False, lazy="select")
    
    # Self-referential relationships
    created_users = relationship("User", foreign_keys="User.created_by", remote_side=[id])
    updated_users = relationship("User", foreign_keys="User.updated_by", remote_side=[id])


class Account(Base):
    __tablename__ = 'account'
    __table_args__ = (
        Index('account_provider_type_provider_account_id_key', 'provider', 'type', 'provider_account_id', unique=True),
        Index('account_provider_type_user_id_key', 'provider', 'type', 'user_id', unique=True)
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)
    properties = Column(JSONB)
    provider = Column(String(255), nullable=False)
    type = Column(String(63), nullable=False)
    provider_account_id = Column(String(255), nullable=False)
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False, index=True)

    user = relationship('User', back_populates='accounts')


class Profile(Base):
    __tablename__ = 'profile'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)
    properties = Column(JSONB)
    avatar_color = Column(Integer)
    avatar_image = Column(String(2048))
    nickname = Column(String(255), unique=True)
    bio = Column(String(16384))
    url = Column(String(2048))
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False, unique=True)
    language_code = Column(String(2), ForeignKey('language.code', ondelete='SET NULL', onupdate='CASCADE'))

    user = relationship('User', back_populates='profile')
    language = relationship('Language', back_populates='profiles')


class StudentProfile(Base):
    __tablename__ = 'student_profile'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)
    properties = Column(JSONB)
    student_id = Column(String(255), unique=True)
    student_email = Column(String(320), unique=True)
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False, unique=True)
    organization_id = Column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)

    user = relationship('User', foreign_keys=[user_id], back_populates="student_profiles", uselist=False)
    organization = relationship('Organization', back_populates='student_profiles')


class Session(Base):
    __tablename__ = 'session'
    __table_args__ = (
        Index(
            'ix_session_user_active',
            'user_id',
            postgresql_where=text("revoked_at IS NULL AND ended_at IS NULL")
        ),
        Index('ix_session_last_seen', 'last_seen_at'),
    )

    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))

    # Unique session identifier per device/login
    sid = Column(UUID, unique=True, nullable=False, server_default=text("uuid_generate_v4()"))

    # User relationship
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)
    user = relationship('User', back_populates='sessions')

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    last_seen_at = Column(DateTime(True))
    expires_at = Column(DateTime(True))

    # Status
    revoked_at = Column(DateTime(True))
    revocation_reason = Column(String(255))
    ended_at = Column(DateTime(True))  # Replaces logout_time

    # Tokens (hashed for security)
    session_id = Column(String(1024), nullable=False)  # Access token hash
    refresh_token_hash = Column(LargeBinary)  # Refresh token hash (binary)
    refresh_expires_at = Column(DateTime(True))
    refresh_counter = Column(Integer, nullable=False, server_default=text("0"))

    # Network context
    created_ip = Column(INET, nullable=False)  # IP at session creation
    last_ip = Column(INET)  # Last seen IP
    user_agent = Column(String(4096))  # Raw user agent string
    device_label = Column(String(512))  # Human-readable device description

    # Metadata and versioning
    version = Column(BigInteger, nullable=False, server_default=text("0"))
    properties = Column(JSONB, server_default=text("'{}'::jsonb"))

    # Legacy fields for backwards compatibility
    created_by = Column(UUID)
    updated_by = Column(UUID)
    logout_time = Column(DateTime(True))  # Deprecated: use ended_at