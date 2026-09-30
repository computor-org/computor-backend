"""Invite-only registration: admission settings, invite kind, referral tracking

Adds to the ``instance_settings`` singleton the registration admission knobs
(``registration_mode``, ``max_registered_users``, ``referral_invites_per_user``,
``pilot_course_ids``); an ``invite_link.kind`` column separating admin invites
from users' referral invites; and ``user.registered_via_invite_id`` /
``user.referred_by_user_id`` recording which invite (and so which referrer)
admitted each new user.

Every default reproduces the behaviour before this migration: registration
stays ``open`` with no user cap, and existing invites are ``admin`` invites.

Revision ID: d9e1f3a5b7c9
Revises: c8d0e2f4a6b8
Create Date: 2026-09-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd9e1f3a5b7c9'
down_revision: Union[str, None] = 'c8d0e2f4a6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('instance_settings', sa.Column(
        'registration_mode', sa.String(16), nullable=False,
        server_default=sa.text("'open'")))
    op.add_column('instance_settings', sa.Column('max_registered_users', sa.BigInteger()))
    op.add_column('instance_settings', sa.Column(
        'referral_invites_per_user', sa.Integer(), nullable=False,
        server_default=sa.text('2')))
    op.add_column('instance_settings', sa.Column(
        'pilot_course_ids', postgresql.JSONB(), nullable=False,
        server_default=sa.text("'[]'::jsonb")))
    op.create_check_constraint(
        'instance_settings_registration_mode_check', 'instance_settings',
        "registration_mode IN ('open', 'invite_only', 'closed')")
    op.create_check_constraint(
        'instance_settings_registered_users_check', 'instance_settings',
        'max_registered_users IS NULL OR max_registered_users >= 0')
    op.create_check_constraint(
        'instance_settings_referral_invites_check', 'instance_settings',
        'referral_invites_per_user >= 0')

    op.add_column('invite_link', sa.Column(
        'kind', sa.String(16), nullable=False, server_default=sa.text("'admin'")))
    op.create_index('ix_invite_link_created_by_kind', 'invite_link', ['created_by', 'kind'])

    op.add_column('user', sa.Column('registered_via_invite_id', postgresql.UUID()))
    op.add_column('user', sa.Column('referred_by_user_id', postgresql.UUID()))
    op.create_foreign_key(
        'user_registered_via_invite_id_fkey', 'user', 'invite_link',
        ['registered_via_invite_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(
        'user_referred_by_user_id_fkey', 'user', 'user',
        ['referred_by_user_id'], ['id'], ondelete='SET NULL')


def _refuse_unsafe_downgrade() -> None:
    """Refuse to drop the admission policy while it is protecting anything.

    The downgrade drops registration_mode, max_registered_users and
    invite_link.kind: a gated instance would silently reopen, the cap would
    vanish, and surviving referral links would turn into ordinary admin
    invites redeemable through the password path.
    """
    bind = op.get_bind()
    gated = bind.execute(sa.text(
        "SELECT count(*) FROM instance_settings "
        "WHERE registration_mode <> 'open' OR max_registered_users IS NOT NULL"
    )).scalar()
    referrals = bind.execute(sa.text(
        "SELECT count(*) FROM invite_link WHERE kind = 'referral' AND revoked_at IS NULL"
    )).scalar()
    if gated or referrals:
        raise RuntimeError(
            "Refusing to downgrade d9e1f3a5b7c9: registration is gated "
            f"(instance_settings rows with a mode other than 'open' or a user cap: {gated}) "
            f"and/or {referrals} unrevoked referral invite(s) exist. This downgrade "
            "would reopen registration, drop the user cap and turn referral links into "
            "password-redeemable admin invites. First set registration_mode='open' and "
            "max_registered_users=NULL, and revoke the referral invites "
            "(UPDATE invite_link SET revoked_at = now() WHERE kind = 'referral'), "
            "then run the downgrade again."
        )


def downgrade() -> None:
    _refuse_unsafe_downgrade()

    op.drop_constraint('user_referred_by_user_id_fkey', 'user', type_='foreignkey')
    op.drop_constraint('user_registered_via_invite_id_fkey', 'user', type_='foreignkey')
    op.drop_column('user', 'referred_by_user_id')
    op.drop_column('user', 'registered_via_invite_id')

    op.drop_index('ix_invite_link_created_by_kind', table_name='invite_link')
    op.drop_column('invite_link', 'kind')

    for name in (
        'instance_settings_referral_invites_check',
        'instance_settings_registered_users_check',
        'instance_settings_registration_mode_check',
    ):
        op.drop_constraint(name, 'instance_settings', type_='check')
    op.drop_column('instance_settings', 'pilot_course_ids')
    op.drop_column('instance_settings', 'referral_invites_per_user')
    op.drop_column('instance_settings', 'max_registered_users')
    op.drop_column('instance_settings', 'registration_mode')
