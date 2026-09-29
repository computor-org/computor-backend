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

_ROLE_ATTRS = (
    "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION "
    "NOBYPASSRLS CONNECTION LIMIT 20"
)

# pg_catalog functions that create large objects: a write that needs no table
# privilege and survives any transaction setting the role can change itself.
_LO_CREATE_FUNCTIONS = ("lo_create(oid)", "lo_creat(integer)", "lo_from_bytea(oid, bytea)")

logger = logging.getLogger("ensure_coder_worker_db_role")


def ensure_role(conn, role: str, password: str, database: str) -> list:
    """Reconcile the role to exactly the definition below, in ONE transaction.

    Runs on an open psycopg2 connection (autocommit off) as the app owner.
    Returns warnings for the hardening steps the connecting user was not
    allowed to perform (non-superuser owner on a managed Postgres).

    - CREATE/ALTER with fixed attributes and the password.
    - Every membership of the role is revoked (pg_read_all_data & co. could
      otherwise be reached with SET ROLE, which NOINHERIT does not stop).
    - Objects it owns are reassigned to the app owner, and DROP OWNED revokes
      every privilege granted to it in this database (tables, sequences,
      functions, schemas, large objects, default privileges, CONNECT/TEMP).
    - PUBLIC loses CREATE on schema public and TEMPORARY on the database (the
      app owner keeps both as owner; migrations run as the owner), and EXECUTE
      on the large-object *creation* functions (re-granted to the app owner).
    - Then exactly: CONNECT, USAGE on public, SELECT (id,
      workspace_app_key_version) on "user"; default_transaction_read_only on.

    A single transaction (plus an advisory lock against concurrent runs)
    means a concurrent rollout never sees the revoked-but-not-yet-granted
    state. default_transaction_read_only is only defence in depth: the role
    can SET it off, so the grants above are what actually bound it.
    """
    from psycopg2 import sql

    r = sql.Identifier(role)
    warnings: list = []
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('computor_coder_worker_role'))")
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        verb = "ALTER" if cur.fetchone() else "CREATE"
        cur.execute(
            sql.SQL(verb + " ROLE {} " + _ROLE_ATTRS + " PASSWORD %s").format(r),
            (password,),
        )
        cur.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(r)
        )
        # Per grantor: on PG16 a membership granted by another role survives a
        # plain REVOKE issued by us.
        cur.execute(
            "SELECT g.rolname, gr.rolname FROM pg_auth_members m "
            "JOIN pg_roles g ON g.oid = m.roleid "
            "JOIN pg_roles u ON u.oid = m.member "
            "JOIN pg_roles gr ON gr.oid = m.grantor WHERE u.rolname = %s",
            (role,),
        )
        for granted, grantor in cur.fetchall():
            cur.execute(
                sql.SQL("REVOKE {} FROM {} GRANTED BY {} CASCADE").format(
                    sql.Identifier(granted), r, sql.Identifier(grantor)
                )
            )
        cur.execute(sql.SQL("REASSIGN OWNED BY {} TO CURRENT_USER").format(r))
        cur.execute(sql.SQL("DROP OWNED BY {}").format(r))

        db = sql.Identifier(database)
        cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        cur.execute(sql.SQL("REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC").format(db))
        for fn in _LO_CREATE_FUNCTIONS:
            cur.execute("SAVEPOINT lo_acl")
            try:
                cur.execute(f"REVOKE EXECUTE ON FUNCTION pg_catalog.{fn} FROM PUBLIC")
                cur.execute(f"GRANT EXECUTE ON FUNCTION pg_catalog.{fn} TO CURRENT_USER")
                cur.execute("RELEASE SAVEPOINT lo_acl")
            except Exception as e:  # not the function owner (managed Postgres)
                cur.execute("ROLLBACK TO SAVEPOINT lo_acl")
                warnings.append(f"could not revoke EXECUTE on {fn} from PUBLIC: {e}")

        cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(db, r))
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(r))
        for table, columns in READABLE_COLUMNS:
            cur.execute(
                sql.SQL("GRANT SELECT ({}) ON TABLE public.{} TO {}").format(
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.Identifier(table),
                    r,
                )
            )
    conn.commit()
    return warnings


def role_ready(conn, role: str) -> bool:
    """True when the worker role exists and can log in."""
    with conn.cursor() as cur:
        cur.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname = %s", (role,))
        row = cur.fetchone()
    return bool(row and row[0])


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
        warnings = ensure_role(conn, role, password, database)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    for warning in warnings:
        logger.warning(f"WARNING: {warning}")
    logger.info(f"Coder worker DB role '{role}' ensured (SELECT on user.id, "
                "user.workspace_app_key_version only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
