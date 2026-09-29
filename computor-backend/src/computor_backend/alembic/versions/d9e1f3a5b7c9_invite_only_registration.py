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


def downgrade() -> None:
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
