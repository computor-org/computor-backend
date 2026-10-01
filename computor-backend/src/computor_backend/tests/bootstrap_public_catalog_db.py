"""Create a disposable synthetic schema for public-catalog integration checks."""
import os
from sqlalchemy import create_engine, text
from computor_backend.model import Base


def main():
    name = os.environ["POSTGRES_DB"]
    if not name.endswith("_test"):
        raise RuntimeError("Only an explicitly named disposable _test database is allowed")
    engine = create_engine("postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}".format(**os.environ))
    with engine.begin() as db:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
        db.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        db.execute(text("CREATE OR REPLACE FUNCTION computor_valid_slug(value text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$ SELECT value ~ '^[a-z0-9]+([_-][a-z0-9]+)*$' $$"))
        db.execute(text("CREATE SEQUENCE IF NOT EXISTS user_unique_fs_number_seq"))
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    main()
