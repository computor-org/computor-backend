from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
from sqlalchemy import create_engine, text

from .config import ANALYTICS_TABLES
from .store import AnalyticsDuckDbStore


class PostgresAnalyticsSource:
    def __init__(
        self,
        database_url: str,
        statement_timeout_ms: int = 300_000,
        application_name: str = "computor_analytics_blue",
        chunk_size: int = 100_000,
    ):
        options = (
            f"-c statement_timeout={statement_timeout_ms} "
            "-c default_transaction_read_only=on "
            f"-c application_name={application_name}"
        )
        self.engine = create_engine(
            database_url,
            future=True,
            connect_args={"options": options},
        )
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def export_snapshot(
        self,
        store: AnalyticsDuckDbStore,
        snapshot_root: Path | str,
        run_id: str | None = None,
        tables: Iterable[str] = ANALYTICS_TABLES,
        progress: Callable[[str, dict[str, object]], None] | None = None,
    ) -> Path:
        run = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        root = Path(snapshot_root) / f"run={run}"
        root.mkdir(parents=True, exist_ok=True)
        with self.engine.connect() as conn:
            conn.execute(text("BEGIN READ ONLY"))
            try:
                manifest = {
                    "run_id": run,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "tables": {},
                }
                for table in tables:
                    if progress:
                        progress(table, {"stage": "exporting"})
                    manifest["tables"][table] = self._export_table(
                        conn.execution_options(stream_results=True),
                        store,
                        root,
                        table,
                    )
                    if progress:
                        progress(table, manifest["tables"][table])
                manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
                (root / "manifest.json").write_text(
                    json.dumps(manifest, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            finally:
                conn.rollback()
        return root

    def _export_table(
        self,
        conn,
        store: AnalyticsDuckDbStore,
        root: Path,
        table: str,
    ) -> dict[str, object]:
        table_root = root / f"table={table}"
        table_root.mkdir(parents=True, exist_ok=True)
        store.drop_table(table)

        row_count = 0
        high_water_marks: dict[str, object] = {}
        loaded_any = False
        for part_index, frame in enumerate(
            pd.read_sql_query(
                text(f"SELECT * FROM {_quoted_identifier(table)}"),
                conn,
                chunksize=self.chunk_size,
            )
        ):
            if frame.empty:
                continue
            if loaded_any:
                store.append_table_from_frame(table, frame)
            else:
                store.replace_table_from_frame(table, frame)
                loaded_any = True
            store.write_frame_parquet(
                frame,
                table_root / f"part-{part_index:05d}.parquet",
            )
            row_count += int(len(frame.index))
            _merge_high_water_marks(high_water_marks, frame)

        if not loaded_any:
            frame = pd.read_sql_query(
                text(f"SELECT * FROM {_quoted_identifier(table)} WHERE false"),
                conn,
            )
            store.replace_table_from_frame(table, frame)
            store.write_table_parquet(table, table_root / "part-00000.parquet")

        return {
            "rows": row_count,
            "high_water_marks": _format_high_water_marks(high_water_marks),
            "parts": len(list(table_root.glob("*.parquet"))),
        }


def _merge_high_water_marks(
    high_water_marks: dict[str, object],
    frame: pd.DataFrame,
) -> None:
    for column in ("updated_at", "created_at", "uploaded_at", "graded_at"):
        if column in frame.columns and not frame.empty:
            value = frame[column].max()
            if pd.isna(value):
                continue
            if column not in high_water_marks or value > high_water_marks[column]:
                high_water_marks[column] = value


def _format_high_water_marks(high_water_marks: dict[str, object]) -> dict[str, str]:
    return {
        column: value.isoformat() if hasattr(value, "isoformat") else str(value)
        for column, value in high_water_marks.items()
    }


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
