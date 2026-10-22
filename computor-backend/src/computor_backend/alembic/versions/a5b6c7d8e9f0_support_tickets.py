"""Support tickets: ticket tables, internal message visibility, support roles

computor-org/issues#520 (MVP). Adds

* ``ticket`` (+ ``ticket_number_seq``), ``ticket_event`` (audit trail),
  ``ticket_mail_message`` (Message-ID -> ticket, unique: idempotent import),
  ``ticket_attachment`` and ``support_mail_state`` (IMAP cursor);
* ``message.ticket_id`` and ``message.visibility`` ('public' | 'internal');
  ``message.author_id`` becomes nullable for ticket rows only (CHECK), and
  ticket rows can carry no course/user target and no parent (CHECK), so the
  course-messaging read paths cannot reach them;
* ``message.content`` becomes TEXT (mail bodies exceed 16384 characters;
  varchar -> text needs no table rewrite in PostgreSQL);
* builtin roles ``_support`` (handle tickets) and ``_support_agent`` (AI:
  read and internal notes only). Authorisation is by role in the /support
  endpoints, so neither role needs claims.

Revision ID: a5b6c7d8e9f0
Revises: 7218c1b74fde
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a5b6c7d8e9f0"
down_revision: str | None = "7218c1b74fde"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_cols():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(), nullable=True),
    ]


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS ticket_number_seq")
    op.create_table(
        "ticket",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("version", sa.BigInteger(), server_default=sa.text("0"), nullable=True),
        *_audit_cols(),
        sa.Column("number", sa.BigInteger(), server_default=sa.text("nextval('ticket_number_seq')"),
                  nullable=False),
        sa.Column("subject", sa.String(998), nullable=False),
        sa.Column("channel", sa.String(16), server_default=sa.text("'mail'"), nullable=False),
        sa.Column("status", sa.String(16), server_default=sa.text("'open'"), nullable=False),
        sa.Column("priority", sa.String(16), server_default=sa.text("'normal'"), nullable=False),
        sa.Column("restricted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("mailbox_address", sa.String(320), nullable=True),
        sa.Column("reporter_user_id", postgresql.UUID(), nullable=True),
        sa.Column("reporter_email", sa.String(320), nullable=True),
        sa.Column("reporter_name", sa.String(255), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(), nullable=True),
        sa.Column("course_id", postgresql.UUID(), nullable=True),
        sa.Column("course_content_id", postgresql.UUID(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'waiting', 'done')",
                           name="ticket_status_check"),
        sa.CheckConstraint("channel IN ('mail', 'web', 'vscode')", name="ticket_channel_check"),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high')", name="ticket_priority_check"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignee_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_content_id"], ["course_content.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="ticket_number_key"),
    )
    op.execute("ALTER SEQUENCE ticket_number_seq OWNED BY ticket.number")
    op.create_index("ticket_status_idx", "ticket", ["status", "last_message_at"])
    op.create_index("ticket_assignee_idx", "ticket", ["assignee_id", "status"])
    op.execute("""
        CREATE TRIGGER ticket_audit_trigger
        BEFORE INSERT OR UPDATE ON "ticket"
        FOR EACH ROW
        EXECUTE FUNCTION set_audit_fields();
    """)

    op.create_table(
        "ticket_event",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["ticket.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ticket_event_ticket_idx", "ticket_event", ["ticket_id", "created_at"])

    # message: ticket link, visibility, nullable author for inbound mail.
    op.add_column("message", sa.Column("ticket_id", postgresql.UUID(), nullable=True))
    op.add_column("message", sa.Column("visibility", sa.String(16),
                                       server_default=sa.text("'public'"), nullable=False))
    op.create_foreign_key("message_ticket_id_fkey", "message", "ticket", ["ticket_id"], ["id"],
                          ondelete="CASCADE", onupdate="RESTRICT")
    op.create_index("msg_ticket_created_idx", "message", ["ticket_id", "created_at"])
    op.alter_column("message", "author_id", existing_type=postgresql.UUID(), nullable=True)
    op.alter_column("message", "content", existing_type=sa.String(16384), type_=sa.Text(),
                    existing_nullable=False)
    op.create_check_constraint("msg_visibility_check", "message",
                               "visibility IN ('public', 'internal')")
    op.create_check_constraint("msg_author_or_ticket_check", "message",
                               "author_id IS NOT NULL OR ticket_id IS NOT NULL")
    op.create_check_constraint("msg_internal_ticket_only_check", "message",
                               "visibility = 'public' OR ticket_id IS NOT NULL")
    op.create_check_constraint(
        "msg_ticket_unscoped_check", "message",
        "ticket_id IS NULL OR (parent_id IS NULL AND organization_id IS NULL"
        " AND course_family_id IS NULL AND course_id IS NULL"
        " AND course_content_id IS NULL AND course_group_id IS NULL"
        " AND submission_group_id IS NULL AND course_member_id IS NULL"
        " AND user_id IS NULL)",
    )

    op.create_table(
        "ticket_mail_message",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("mail_message_id", sa.String(998), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(), nullable=False),
        sa.Column("message_id", postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["ticket.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mail_message_id", name="ticket_mail_message_mail_message_id_key"),
    )
    op.create_index("ticket_mail_message_ticket_idx", "ticket_mail_message", ["ticket_id"])

    op.create_table(
        "ticket_attachment",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("message_id", postgresql.UUID(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ticket_attachment_message_idx", "ticket_attachment", ["message_id"])

    op.create_table(
        "support_mail_state",
        sa.Column("folder", sa.Text(), nullable=False),
        sa.Column("uidvalidity", sa.BigInteger(), nullable=False),
        sa.Column("last_uid", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("folder"),
    )

    op.execute("""
        INSERT INTO role (id, title, description, builtin)
        VALUES
          ('_support', 'Support',
           'Handle support tickets (team mail, problem reports): view, claim, assign, reply, set status, internal notes.',
           true),
          ('_support_agent', 'Support Agent',
           'Machine role for AI assistance: read tickets and write internal notes; cannot send, claim, close or publish.',
           true)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM user_role  WHERE role_id IN ('_support', '_support_agent');
        DELETE FROM role_claim WHERE role_id IN ('_support', '_support_agent');
        DELETE FROM role       WHERE id IN ('_support', '_support_agent');
    """)
    op.drop_table("support_mail_state")
    op.drop_index("ticket_attachment_message_idx", table_name="ticket_attachment")
    op.drop_table("ticket_attachment")
    op.drop_index("ticket_mail_message_ticket_idx", table_name="ticket_mail_message")
    op.drop_table("ticket_mail_message")
    # Ticket messages cannot survive without their ticket (no author, no scope).
    op.execute("DELETE FROM message WHERE ticket_id IS NOT NULL")
    op.drop_constraint("msg_ticket_unscoped_check", "message", type_="check")
    op.drop_constraint("msg_internal_ticket_only_check", "message", type_="check")
    op.drop_constraint("msg_author_or_ticket_check", "message", type_="check")
    op.drop_constraint("msg_visibility_check", "message", type_="check")
    op.alter_column("message", "content", existing_type=sa.Text(), type_=sa.String(16384),
                    existing_nullable=False)
    op.alter_column("message", "author_id", existing_type=postgresql.UUID(), nullable=False)
    op.drop_index("msg_ticket_created_idx", table_name="message")
    op.drop_constraint("message_ticket_id_fkey", "message", type_="foreignkey")
    op.drop_column("message", "visibility")
    op.drop_column("message", "ticket_id")
    op.drop_index("ticket_event_ticket_idx", table_name="ticket_event")
    op.drop_table("ticket_event")
    op.execute('DROP TRIGGER IF EXISTS ticket_audit_trigger ON "ticket"')
    op.drop_index("ticket_assignee_idx", table_name="ticket")
    op.drop_index("ticket_status_idx", table_name="ticket")
    op.drop_table("ticket")
    op.execute("DROP SEQUENCE IF EXISTS ticket_number_seq")
