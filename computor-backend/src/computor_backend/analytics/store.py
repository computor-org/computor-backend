from __future__ import annotations

from pathlib import Path
from typing import Iterable

import duckdb

from .config import ANALYTICS_TABLES


class AnalyticsDuckDbStore:
    def __init__(self, database_path: Path | str = ":memory:"):
        self.database_path = Path(database_path) if database_path != ":memory:" else database_path
        if isinstance(self.database_path, Path):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(self.database_path))

    def close(self) -> None:
        self.connection.close()

    def load_parquet_snapshot(
        self,
        snapshot_root: Path | str,
        tables: Iterable[str] = ANALYTICS_TABLES,
    ) -> None:
        root = Path(snapshot_root)
        for table in tables:
            parquet_glob = root / f"table={table}" / "*.parquet"
            if not list(parquet_glob.parent.glob("*.parquet")):
                continue
            self.connection.execute(
                f"CREATE OR REPLACE TABLE {_identifier(table)} AS "
                "SELECT * FROM read_parquet(?)",
                [str(parquet_glob)],
            )

    def drop_table(self, table: str) -> None:
        self.connection.execute(f"DROP TABLE IF EXISTS {_identifier(table)}")

    def replace_table_from_frame(self, table: str, frame: object) -> None:
        view_name = f"__analytics_import_{table}"
        self.connection.register(view_name, frame)
        try:
            self.connection.execute(
                f"CREATE OR REPLACE TABLE {_identifier(table)} AS "
                f"SELECT * FROM {_identifier(view_name)}"
            )
        finally:
            self.connection.unregister(view_name)

    def append_table_from_frame(self, table: str, frame: object) -> None:
        view_name = f"__analytics_import_{table}"
        self.connection.register(view_name, frame)
        try:
            self.connection.execute(
                f"INSERT INTO {_identifier(table)} SELECT * FROM {_identifier(view_name)}"
            )
        finally:
            self.connection.unregister(view_name)

    def write_frame_parquet(self, frame: object, destination: Path | str) -> None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        view_name = "__analytics_export_frame"
        self.connection.register(view_name, frame)
        try:
            self.connection.execute(
                f"COPY (SELECT * FROM {_identifier(view_name)}) "
                f"TO {_string_literal(path)} (FORMAT PARQUET)"
            )
        finally:
            self.connection.unregister(view_name)

    def write_table_parquet(self, table: str, destination: Path | str) -> None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection.execute(
            f"COPY (SELECT * FROM {_identifier(table)}) "
            f"TO {_string_literal(path)} (FORMAT PARQUET)"
        )


def _identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _string_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"
