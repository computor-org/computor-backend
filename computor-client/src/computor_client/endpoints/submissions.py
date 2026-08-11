"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Union

from computor_types.artifacts import (
    SubmissionArtifactGet,
    SubmissionArtifactList,
    SubmissionArtifactUpdate,
    SubmissionGradeCreate,
    SubmissionGradeDetail,
    SubmissionGradeList,
    SubmissionGradeUpdate,
    SubmissionReviewCreate,
    SubmissionReviewListItem,
    SubmissionReviewUpdate,
)
from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultList,
    ResultUpdate,
)
from computor_types.submissions import SubmissionUploadResponseModel

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class SubmissionsClient:
    """
    Client for submissions endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list_artifacts(
        self,
        **kwargs: Any,
    ) -> List[SubmissionArtifactList]:
        """List Submission Artifacts"""
        response = await self._http.get("/submissions/artifacts", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionArtifactList.model_validate(item) for item in data]
        return []

    async def artifacts(
        self,
        file: bytes,
        submission_create: str,
        **kwargs: Any,
    ) -> SubmissionUploadResponseModel:
        """Upload Submission"""
        files = {"file": file}
        form_fields = {"submission_create": submission_create}
        response = await self._http.post("/submissions/artifacts", files=files, data=form_fields, params=kwargs)
        return SubmissionUploadResponseModel.model_validate(response.json())

    async def get_artifacts_download(
        self,
        **kwargs: Any,
    ) -> bytes:
        """Download Latest Submission"""
        response = await self._http.get("/submissions/artifacts/download", params=kwargs)
        return response.content

    async def get_artifacts(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> SubmissionArtifactGet:
        """Get Submission Artifact"""
        response = await self._http.get(f"/submissions/artifacts/{quote_path(artifact_id)}", params=kwargs)
        return SubmissionArtifactGet.model_validate(response.json())

    async def update_artifacts(
        self,
        artifact_id: str,
        data: Union[SubmissionArtifactUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionArtifactGet:
        """Update Submission Artifact"""
        response = await self._http.patch(f"/submissions/artifacts/{quote_path(artifact_id)}", json_data=data, params=kwargs)
        return SubmissionArtifactGet.model_validate(response.json())

    async def get_artifacts_download_by_artifact_id(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Submission Artifact"""
        response = await self._http.get(f"/submissions/artifacts/{quote_path(artifact_id)}/download", params=kwargs)
        return response.content

    async def list_artifacts_grades(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> List[SubmissionGradeList]:
        """List Artifact Grades"""
        response = await self._http.get(f"/submissions/artifacts/{quote_path(artifact_id)}/grades", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionGradeList.model_validate(item) for item in data]
        return []

    async def artifacts_grades(
        self,
        artifact_id: str,
        data: Union[SubmissionGradeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGradeDetail:
        """Create Artifact Grade Endpoint"""
        response = await self._http.post(f"/submissions/artifacts/{quote_path(artifact_id)}/grades", json_data=data, params=kwargs)
        return SubmissionGradeDetail.model_validate(response.json())

    async def list_artifacts_reviews(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> List[SubmissionReviewListItem]:
        """List Artifact Reviews"""
        response = await self._http.get(f"/submissions/artifacts/{quote_path(artifact_id)}/reviews", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionReviewListItem.model_validate(item) for item in data]
        return []

    async def artifacts_reviews(
        self,
        artifact_id: str,
        data: Union[SubmissionReviewCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionReviewListItem:
        """Create Artifact Review Endpoint"""
        response = await self._http.post(f"/submissions/artifacts/{quote_path(artifact_id)}/reviews", json_data=data, params=kwargs)
        return SubmissionReviewListItem.model_validate(response.json())

    async def artifacts_test(
        self,
        artifact_id: str,
        data: Union[ResultCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultList:
        """Create Test Result Endpoint"""
        response = await self._http.post(f"/submissions/artifacts/{quote_path(artifact_id)}/test", json_data=data, params=kwargs)
        return ResultList.model_validate(response.json())

    async def list_artifacts_tests(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> List[ResultGet]:
        """List Artifact Test Results"""
        response = await self._http.get(f"/submissions/artifacts/{quote_path(artifact_id)}/tests", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ResultGet.model_validate(item) for item in data]
        return []

    async def list_grades(
        self,
        **kwargs: Any,
    ) -> List[SubmissionGradeList]:
        """List Grades"""
        response = await self._http.get("/submissions/grades", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionGradeList.model_validate(item) for item in data]
        return []

    async def delete_grades(
        self,
        grade_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Artifact Grade"""
        await self._http.delete(f"/submissions/grades/{quote_path(grade_id)}", params=kwargs)
        return

    async def update_grades(
        self,
        grade_id: str,
        data: Union[SubmissionGradeUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGradeDetail:
        """Update Artifact Grade"""
        response = await self._http.patch(f"/submissions/grades/{quote_path(grade_id)}", json_data=data, params=kwargs)
        return SubmissionGradeDetail.model_validate(response.json())

    async def delete_reviews(
        self,
        review_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Artifact Review"""
        await self._http.delete(f"/submissions/reviews/{quote_path(review_id)}", params=kwargs)
        return

    async def update_reviews(
        self,
        review_id: str,
        data: Union[SubmissionReviewUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionReviewListItem:
        """Update Artifact Review"""
        response = await self._http.patch(f"/submissions/reviews/{quote_path(review_id)}", json_data=data, params=kwargs)
        return SubmissionReviewListItem.model_validate(response.json())

    async def update_tests(
        self,
        test_id: str,
        data: Union[ResultUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultList:
        """Update Test Result Endpoint"""
        response = await self._http.patch(f"/submissions/tests/{quote_path(test_id)}", json_data=data, params=kwargs)
        return ResultList.model_validate(response.json())

