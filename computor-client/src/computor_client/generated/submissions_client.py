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

from computor_client.base import FileOperationClient


class SubmissionsClient(FileOperationClient):
    """Client for /submissions endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submissions",
        )

    async def post_submissions_artifacts(self, user_id: Optional[str] = None) -> SubmissionUploadResponseModel:
        """Upload Submission"""
        data = await self._request("POST", "/artifacts")
        if data:
            return SubmissionUploadResponseModel.model_validate(data)
        return data

    async def get_submissions_artifacts(self, course_content_id: Optional[str] = None, with_latest_result: Optional[str] = None, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, submission_group_id: Optional[str] = None, uploaded_by_course_member_id: Optional[str] = None, content_type: Optional[str] = None, version_identifier: Optional[str] = None, submit: Optional[str] = None, user_id: Optional[str] = None) -> List[SubmissionArtifactList]:
        """List Submission Artifacts"""
        params = {k: v for k, v in locals().items() if k in ['course_content_id', 'with_latest_result', 'skip', 'limit', 'id', 'submission_group_id', 'uploaded_by_course_member_id', 'content_type', 'version_identifier', 'submit', 'user_id'] and v is not None}
        data = await self._request("GET", "/artifacts", params=params)
        if isinstance(data, list):
            return [SubmissionArtifactList.model_validate(item) for item in data]
        return data

    async def get_submission_artifact_by_artifact_id(self, artifact_id: str, user_id: Optional[str] = None) -> SubmissionArtifactGet:
        """Get Submission Artifact"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/artifacts/{artifact_id}", params=params)
        if data:
            return SubmissionArtifactGet.model_validate(data)
        return data

    async def patch_submission_artifact_by_artifact_id(self, artifact_id: str, payload: SubmissionArtifactUpdate, user_id: Optional[str] = None) -> SubmissionArtifactGet:
        """Update Submission Artifact"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/artifacts/{artifact_id}", json=json_data)
        if data:
            return SubmissionArtifactGet.model_validate(data)
        return data

    async def get_submissions_artifacts_download(self, submission_group_id: Optional[str] = None, course_content_id: Optional[str] = None, course_member_id: Optional[str] = None, version_identifier: Optional[str] = None, submit_only: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Download Latest Submission"""
        params = {k: v for k, v in locals().items() if k in ['submission_group_id', 'course_content_id', 'course_member_id', 'version_identifier', 'submit_only', 'user_id'] and v is not None}
        data = await self._request("GET", "/artifacts/download", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_submission_artifact_download(self, artifact_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Download Submission Artifact"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/artifacts/{artifact_id}/download", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_submission_artifact_grade(self, artifact_id: str, payload: SubmissionGradeCreate, user_id: Optional[str] = None) -> SubmissionGradeDetail:
        """Create Artifact Grade Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/artifacts/{artifact_id}/grades", json=json_data)
        if data:
            return SubmissionGradeDetail.model_validate(data)
        return data

    async def get_submission_artifact_grade(self, artifact_id: str, user_id: Optional[str] = None) -> List[SubmissionGradeListItem]:
        """List Artifact Grades"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/artifacts/{artifact_id}/grades", params=params)
        if isinstance(data, list):
            return [SubmissionGradeListItem.model_validate(item) for item in data]
        return data

    async def patch_submission_grade_by_grade_id(self, grade_id: str, payload: SubmissionGradeUpdate, user_id: Optional[str] = None) -> SubmissionGradeDetail:
        """Update Artifact Grade"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/grades/{grade_id}", json=json_data)
        if data:
            return SubmissionGradeDetail.model_validate(data)
        return data

    async def delete_submission_grade_by_grade_id(self, grade_id: str, user_id: Optional[str] = None) -> Any:
        """Delete Artifact Grade"""
        data = await self._request("DELETE", f"/grades/{grade_id}")

    async def post_submission_artifact_review(self, artifact_id: str, payload: SubmissionReviewCreate, user_id: Optional[str] = None) -> SubmissionReviewListItem:
        """Create Artifact Review"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/artifacts/{artifact_id}/reviews", json=json_data)
        if data:
            return SubmissionReviewListItem.model_validate(data)
        return data

    async def get_submission_artifact_review(self, artifact_id: str, user_id: Optional[str] = None) -> List[SubmissionReviewListItem]:
        """List Artifact Reviews"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/artifacts/{artifact_id}/reviews", params=params)
        if isinstance(data, list):
            return [SubmissionReviewListItem.model_validate(item) for item in data]
        return data

    async def patch_submission_review_by_review_id(self, review_id: str, payload: SubmissionReviewUpdate, user_id: Optional[str] = None) -> SubmissionReviewListItem:
        """Update Artifact Review"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/reviews/{review_id}", json=json_data)
        if data:
            return SubmissionReviewListItem.model_validate(data)
        return data

    async def delete_submission_review_by_review_id(self, review_id: str, user_id: Optional[str] = None) -> Any:
        """Delete Artifact Review"""
        data = await self._request("DELETE", f"/reviews/{review_id}")

    async def post_submission_artifact_test(self, artifact_id: str, payload: ResultCreate, user_id: Optional[str] = None) -> ResultList:
        """Create Test Result"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/artifacts/{artifact_id}/test", json=json_data)
        if data:
            return ResultList.model_validate(data)
        return data

    async def get_submission_artifact_test(self, artifact_id: str, user_id: Optional[str] = None) -> List[ResultList]:
        """List Artifact Test Results"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/artifacts/{artifact_id}/tests", params=params)
        if isinstance(data, list):
            return [ResultList.model_validate(item) for item in data]
        return data

    async def patch_submission_test_by_test_id(self, test_id: str, payload: ResultUpdate, user_id: Optional[str] = None) -> ResultList:
        """Update Test Result"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/tests/{test_id}", json=json_data)
        if data:
            return ResultList.model_validate(data)
        return data
