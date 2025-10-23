"""Auto-generated client for /submissions endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.artifacts import (
    SubmissionArtifactGet,
    SubmissionArtifactList,
    SubmissionArtifactUpdate,
    SubmissionGradeCreate,
    SubmissionGradeDetail,
    SubmissionGradeListItem,
    SubmissionGradeUpdate,
    SubmissionReviewCreate,
    SubmissionReviewListItem,
    SubmissionReviewUpdate,
)
from computor_types.results import (
    ResultCreate,
    ResultList,
    ResultUpdate,
)
from computor_types.submissions import SubmissionUploadResponseModel

from computor_client.base import BaseEndpointClient


class SubmissionsClient(BaseEndpointClient):
    """Client for /submissions endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submissions",
        )

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_submission_test_by_test_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_submission_review_by_review_id(id)

    async def post_submissions_artifacts(self, ) -> SubmissionUploadResponseModel:
        """Upload Submission"""
        data = await self._request("POST", "/artifacts")
        if data:
            return SubmissionUploadResponseModel.model_validate(data)
        return data

    async def get_submissions_artifacts(self, submission_group_id: Optional[str] = None, course_content_id: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None) -> List[SubmissionArtifactList]:
        """List Submission Artifacts"""
        params = {k: v for k, v in locals().items() if k in ['submission_group_id', 'course_content_id', 'limit', 'offset'] and v is not None}
        data = await self._request("GET", "/artifacts", params=params)
        if isinstance(data, list):
            return [SubmissionArtifactList.model_validate(item) for item in data]
        return data

    async def get_submission_artifact_by_artifact_id(self, artifact_id: str) -> SubmissionArtifactGet:
        """Get Submission Artifact"""
        data = await self._request("GET", f"/artifacts/{artifact_id}")
        if data:
            return SubmissionArtifactGet.model_validate(data)
        return data

    async def patch_submission_artifact_by_artifact_id(self, artifact_id: str, payload: SubmissionArtifactUpdate) -> SubmissionArtifactGet:
        """Update Submission Artifact"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/artifacts/{artifact_id}", json=json_data)
        if data:
            return SubmissionArtifactGet.model_validate(data)
        return data

    async def post_submission_artifact_grade(self, artifact_id: str, payload: SubmissionGradeCreate) -> SubmissionGradeDetail:
        """Create Artifact Grade Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/artifacts/{artifact_id}/grades", json=json_data)
        if data:
            return SubmissionGradeDetail.model_validate(data)
        return data

    async def get_submission_artifact_grade(self, artifact_id: str) -> List[SubmissionGradeListItem]:
        """List Artifact Grades"""
        data = await self._request("GET", f"/artifacts/{artifact_id}/grades")
        if isinstance(data, list):
            return [SubmissionGradeListItem.model_validate(item) for item in data]
        return data

    async def patch_submission_grade_by_grade_id(self, grade_id: str, payload: SubmissionGradeUpdate) -> SubmissionGradeDetail:
        """Update Artifact Grade"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/grades/{grade_id}", json=json_data)
        if data:
            return SubmissionGradeDetail.model_validate(data)
        return data

    async def delete_submission_grade_by_grade_id(self, grade_id: str) -> Any:
        """Delete Artifact Grade"""
        data = await self._request("DELETE", f"/grades/{grade_id}")

    async def post_submission_artifact_review(self, artifact_id: str, payload: SubmissionReviewCreate) -> SubmissionReviewListItem:
        """Create Artifact Review"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/artifacts/{artifact_id}/reviews", json=json_data)
        if data:
            return SubmissionReviewListItem.model_validate(data)
        return data

    async def get_submission_artifact_review(self, artifact_id: str) -> List[SubmissionReviewListItem]:
        """List Artifact Reviews"""
        data = await self._request("GET", f"/artifacts/{artifact_id}/reviews")
        if isinstance(data, list):
            return [SubmissionReviewListItem.model_validate(item) for item in data]
        return data

    async def patch_submission_review_by_review_id(self, review_id: str, payload: SubmissionReviewUpdate) -> SubmissionReviewListItem:
        """Update Artifact Review"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/reviews/{review_id}", json=json_data)
        if data:
            return SubmissionReviewListItem.model_validate(data)
        return data

    async def delete_submission_review_by_review_id(self, review_id: str) -> Any:
        """Delete Artifact Review"""
        data = await self._request("DELETE", f"/reviews/{review_id}")

    async def post_submission_artifact_test(self, artifact_id: str, payload: ResultCreate) -> ResultList:
        """Create Test Result"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/artifacts/{artifact_id}/test", json=json_data)
        if data:
            return ResultList.model_validate(data)
        return data

    async def get_submission_artifact_test(self, artifact_id: str) -> List[ResultList]:
        """List Artifact Test Results"""
        data = await self._request("GET", f"/artifacts/{artifact_id}/tests")
        if isinstance(data, list):
            return [ResultList.model_validate(item) for item in data]
        return data

    async def patch_submission_test_by_test_id(self, test_id: str, payload: ResultUpdate) -> ResultList:
        """Update Test Result"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/tests/{test_id}", json=json_data)
        if data:
            return ResultList.model_validate(data)
        return data
