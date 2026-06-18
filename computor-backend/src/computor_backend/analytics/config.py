from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ANALYTICS_TABLES = (
    "course",
    "course_member",
    "user",
    "student_profile",
    "course_content_kind",
    "course_content_type",
    "course_content",
    "submission_group",
    "submission_group_member",
    "submission_artifact",
    "submission_grade",
    "result",
)


@dataclass(frozen=True)
class AnalyticsCutoffs:
    submission: datetime | None = None
    grading: datetime | None = None

    def normalized(self) -> "AnalyticsCutoffs":
        return AnalyticsCutoffs(
            submission=_as_utc(self.submission),
            grading=_as_utc(self.grading),
        )


@dataclass(frozen=True)
class AnalyticsStorageConfig:
    root: Path
    source_name: str = "green"

    @property
    def raw_root(self) -> Path:
        return self.root / "raw" / f"source={self.source_name}"

    @property
    def duckdb_path(self) -> Path:
        return self.root / "duckdb" / "analytics.duckdb"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
