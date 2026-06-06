from typing import Literal, Optional
from pydantic import BaseModel

GitProviderType = Literal['gitlab', 'forgejo', 'github']


class GitProviderCreate(BaseModel):
    organization_id: str
    type: GitProviderType
    url: str
    token: str  # plaintext — encrypted before storage


class GitProviderGet(BaseModel):
    id: str
    organization_id: str
    type: GitProviderType
    url: str
    # token is never returned


class OrgProviderResult(BaseModel):
    provider_entity_id: str      # group_id (GitLab) or org name (Forgejo)
    properties: dict             # provider-specific metadata to store on the organization


class FamilyProviderResult(BaseModel):
    provider_entity_id: str      # subgroup_id (GitLab) or team_id (Forgejo)
    properties: dict


class CourseProviderResult(BaseModel):
    provider_entity_id: str
    properties: dict


class StudentRepoResult(BaseModel):
    http_url: str
    ssh_url: str
    web_url: str
    provider_project_id: str
    properties: dict
