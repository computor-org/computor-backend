"""Create/refresh the restricted Postgres role of the coder temporal worker.

The coder worker (temporal-worker-coder: docker socket, Coder admin API,
template pushes) touches the app database for exactly one thing: resolving a
workspace owner's current app-credential key version during a template
rollout (coder/service.py ``workspace_app_credentials_for_owner``), i.e.

    SELECT id                       FROM "user" WHERE id = :uid
    SELECT workspace_app_key_version FROM "user" WHERE id = :uid

So instead of the app owner's POSTGRES_PASSWORD it gets a login role that can
read those two columns and nothing else, with read-only transactions.

Idempotent; run after ``alembic upgrade head`` with the app owner's
credentials (docker/api/startup.bash, api.sh, migrations.sh). No-op when
CODER_WORKER_DB_PASSWORD is unset, so deployments without Coder are untouched.

Env: CODER_WORKER_DB_USER (default computor_coder_worker),
CODER_WORKER_DB_PASSWORD, plus the usual POSTGRES_* of the app owner.
"""

import logging
import os
import sys

DEFAULT_ROLE = "computor_coder_worker"

# (table, columns) the role may SELECT. Keep in lockstep with the queries in
# coder/service.py that run on the coder worker.
READABLE_COLUMNS = (("user", ("id", "workspace_app_key_version")),)

_ROLE_ATTRS = "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION"

logger = logging.getLogger("ensure_coder_worker_db_role")


def ensure_role(conn, role: str, password: str, database: str) -> None:
    """Apply the role definition on an open psycopg2 connection (autocommit)."""
    from psycopg2 import sql

    r = sql.Identifier(role)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        verb = "ALTER" if cur.fetchone() else "CREATE"
        cur.execute(
            sql.SQL(verb + " ROLE {} " + _ROLE_ATTRS + " PASSWORD %s").format(r),
            (password,),
        )
        cur.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(r)
        )
        # Drop anything granted earlier (by hand or by an older version of this
        # script) so the grant set below is the whole truth. Revoking at table
        # level also revokes the column-level privileges.
        cur.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(r))
        cur.execute(
            sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}").format(r)
        )
        cur.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database), r
            )
        )
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(r))
        for table, columns in READABLE_COLUMNS:
            cur.execute(
                sql.SQL("GRANT SELECT ({}) ON TABLE public.{} TO {}").format(
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.Identifier(table),
                    r,
                )
            )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    password = os.environ.get("CODER_WORKER_DB_PASSWORD", "")
    if not password:
        logger.info("CODER_WORKER_DB_PASSWORD unset; coder worker DB role not managed.")
        return 0
    role = os.environ.get("CODER_WORKER_DB_USER") or DEFAULT_ROLE

    import psycopg2

    database = os.environ["POSTGRES_DB"]
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=database,
    )
    try:
        conn.autocommit = True
        ensure_role(conn, role, password, database)
    finally:
        conn.close()
    logger.info(f"Coder worker DB role '{role}' ensured (SELECT on user.id, "
                "user.workspace_app_key_version only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
