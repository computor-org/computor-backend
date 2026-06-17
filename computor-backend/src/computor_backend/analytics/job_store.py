from __future__ import annotations

import json
from pathlib import Path
import re

from computor_backend.exceptions import BadRequestException
from computor_types.analytics import AnalyticsJobStatus


class AnalyticsJobStore:
    def __init__(self, root: Path | str):
        self.root = Path(root) / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, job: AnalyticsJobStatus) -> AnalyticsJobStatus:
        path = self._path(job.job_id)
        path.write_text(
            json.dumps(job.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return job

    def get(self, job_id: str) -> AnalyticsJobStatus | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        return AnalyticsJobStatus.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, course_id: str | None = None, limit: int = 20) -> list[AnalyticsJobStatus]:
        jobs = []
        for path in self.root.glob("*.json"):
            job = AnalyticsJobStatus.model_validate_json(path.read_text(encoding="utf-8"))
            if course_id is None or job.course_id == str(course_id):
                jobs.append(job)
        jobs.sort(key=lambda job: job.created_at, reverse=True)
        return jobs[:limit]

    def latest_for_course(self, course_id: str) -> AnalyticsJobStatus | None:
        jobs = self.list(course_id=course_id, limit=1)
        return jobs[0] if jobs else None

    def _path(self, job_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise BadRequestException("Invalid analytics job id")
        return self.root / f"{job_id}.json"
