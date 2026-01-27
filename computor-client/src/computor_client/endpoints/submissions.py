"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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
    ResultGet,
    ResultList,
    ResultUpdate,
)
from computor_types.submissions import SubmissionUploadResponseModel

from computor_client.http import AsyncHTTPClient


class SubmissionsClient:
    """
    Client for submissions endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def artifacts(
        self,
        **kwargs: Any,
    ) -> SubmissionUploadResponseModel:
        """Upload Submission"""
        response = await self._http.post(f"/submissions/artifacts", params=kwargs)
        return SubmissionUploadResponseModel.model_validate(response.json())

    async def get_artifacts(
        self,
        **kwargs: Any,
    ) -> List[SubmissionArtifactList]:
        """List Submission Artifacts"""
        response = await self._http.get(f"/submissions/artifacts", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionArtifactList.model_validate(item) for item in data]
        return []

    async def get_missions_artifacts_artifact_id(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> SubmissionArtifactGet:
        """Get Submission Artifact"""
        response = await self._http.get(f"/submissions/artifacts/{artifact_id}", params=kwargs)
        return SubmissionArtifactGet.model_validate(response.json())

    async def patch_artifacts(
        self,
        artifact_id: str,
        data: Union[SubmissionArtifactUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionArtifactGet:
        """Update Submission Artifact"""
        response = await self._http.patch(f"/submissions/artifacts/{artifact_id}", json_data=data, params=kwargs)
        return SubmissionArtifactGet.model_validate(response.json())

    async def artifacts_download(
        self,
        **kwargs: Any,
    ) -> bytes:
        """Download Latest Submission"""
        response = await self._http.get(f"/submissions/artifacts/download", params=kwargs)
        return response.content

    async def get_artifacts_download(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Submission Artifact"""
        response = await self._http.get(f"/submissions/artifacts/{artifact_id}/download", params=kwargs)
        return response.content

    async def artifacts_grades(
        self,
        artifact_id: str,
        data: Union[SubmissionGradeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGradeDetail:
        """Create Artifact Grade Endpoint"""
        response = await self._http.post(f"/submissions/artifacts/{artifact_id}/grades", json_data=data, params=kwargs)
        return SubmissionGradeDetail.model_validate(response.json())

    async def get_artifacts_grades(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> List[SubmissionGradeListItem]:
        """List Artifact Grades"""
        response = await self._http.get(f"/submissions/artifacts/{artifact_id}/grades", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionGradeListItem.model_validate(item) for item in data]
        return []

    async def grades(
        self,
        grade_id: str,
        data: Union[SubmissionGradeUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGradeDetail:
        """Update Artifact Grade"""
        response = await self._http.patch(f"/submissions/grades/{grade_id}", json_data=data, params=kwargs)
        return SubmissionGradeDetail.model_validate(response.json())

    async def delete_grades(
        self,
        grade_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Artifact Grade"""
        await self._http.delete(f"/submissions/grades/{grade_id}", params=kwargs)
        return

    async def artifacts_reviews(
        self,
        artifact_id: str,
        data: Union[SubmissionReviewCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionReviewListItem:
        """Create Artifact Review"""
        response = await self._http.post(f"/submissions/artifacts/{artifact_id}/reviews", json_data=data, params=kwargs)
        return SubmissionReviewListItem.model_validate(response.json())

    async def get_artifacts_reviews(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> List[SubmissionReviewListItem]:
        """List Artifact Reviews"""
        response = await self._http.get(f"/submissions/artifacts/{artifact_id}/reviews", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionReviewListItem.model_validate(item) for item in data]
        return []

    async def reviews(
        self,
        review_id: str,
        data: Union[SubmissionReviewUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionReviewListItem:
        """Update Artifact Review"""
        response = await self._http.patch(f"/submissions/reviews/{review_id}", json_data=data, params=kwargs)
        return SubmissionReviewListItem.model_validate(response.json())

    async def delete_reviews(
        self,
        review_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Artifact Review"""
        await self._http.delete(f"/submissions/reviews/{review_id}", params=kwargs)
        return

    async def artifacts_test(
        self,
        artifact_id: str,
        data: Union[ResultCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultList:
        """Create Test Result"""
        response = await self._http.post(f"/submissions/artifacts/{artifact_id}/test", json_data=data, params=kwargs)
        return ResultList.model_validate(response.json())

    async def artifacts_tests(
        self,
        artifact_id: str,
        **kwargs: Any,
    ) -> List[ResultGet]:
        """List Artifact Test Results"""
        response = await self._http.get(f"/submissions/artifacts/{artifact_id}/tests", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ResultGet.model_validate(item) for item in data]
        return []

    async def tests(
        self,
        test_id: str,
        data: Union[ResultUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultList:
        """Update Test Result"""
        response = await self._http.patch(f"/submissions/tests/{test_id}", json_data=data, params=kwargs)
        return ResultList.model_validate(response.json())

