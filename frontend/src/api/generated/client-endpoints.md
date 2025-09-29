# API Client Endpoint Summary

## AccountClient
- Base path: `/accounts`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/accounts` | `AccountCreate` | `AccountGet` |
| `get` | GET | `/accounts/{id}` | — | `AccountGet` |
| `list` | GET | `/accounts` | `AccountQuery` | `AccountList[]` |
| `update` | PATCH | `/accounts/{id}` | `AccountUpdate` | `AccountGet` |
| `delete` | DELETE | `/accounts/{id}` | — | `void` |

## CourseContentDeploymentClient
- Base path: `/deployments`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/deployments` | `CourseContentDeploymentCreate` | `CourseContentDeploymentGet` |
| `get` | GET | `/deployments/{id}` | — | `CourseContentDeploymentGet` |
| `list` | GET | `/deployments` | `CourseContentDeploymentQuery` | `CourseContentDeploymentList[]` |
| `update` | PATCH | `/deployments/{id}` | `CourseContentDeploymentUpdate` | `CourseContentDeploymentGet` |
| `delete` | DELETE | `/deployments/{id}` | — | `void` |

## CourseContentClient
- Base path: `/course-contents`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-contents` | `CourseContentCreate` | `CourseContentGet` |
| `get` | GET | `/course-contents/{id}` | — | `CourseContentGet` |
| `list` | GET | `/course-contents` | `CourseContentQuery` | `CourseContentList[]` |
| `update` | PATCH | `/course-contents/{id}` | `CourseContentUpdate` | `CourseContentGet` |
| `delete` | DELETE | `/course-contents/{id}` | — | `void` |
| `archive` | PATCH | `/course-contents/{id}/archive` | — | `void` |

## CourseContentKindClient
- Base path: `/course-content-kinds`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-content-kinds` | `CourseContentKindCreate` | `CourseContentKindGet` |
| `get` | GET | `/course-content-kinds/{id}` | — | `CourseContentKindGet` |
| `list` | GET | `/course-content-kinds` | `CourseContentKindQuery` | `CourseContentKindList[]` |
| `update` | PATCH | `/course-content-kinds/{id}` | `CourseContentKindUpdate` | `CourseContentKindGet` |
| `delete` | DELETE | `/course-content-kinds/{id}` | — | `void` |

## CourseContentStudentClient
- Base path: `/student-course-contents`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `get` | GET | `/student-course-contents/{id}` | — | `CourseContentStudentGet` |
| `list` | GET | `/student-course-contents` | `CourseContentStudentQuery` | `CourseContentStudentList[]` |
| `update` | PATCH | `/student-course-contents/{id}` | `CourseContentStudentUpdate` | `CourseContentStudentGet` |
| `delete` | DELETE | `/student-course-contents/{id}` | — | `void` |

## CourseContentTypeClient
- Base path: `/course-content-types`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-content-types` | `CourseContentTypeCreate` | `CourseContentTypeGet` |
| `get` | GET | `/course-content-types/{id}` | — | `CourseContentTypeGet` |
| `list` | GET | `/course-content-types` | `CourseContentTypeQuery` | `CourseContentTypeList[]` |
| `update` | PATCH | `/course-content-types/{id}` | `CourseContentTypeUpdate` | `CourseContentTypeGet` |
| `delete` | DELETE | `/course-content-types/{id}` | — | `void` |

## CourseExecutionBackendClient
- Base path: `/course-execution-backends`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-execution-backends` | `CourseExecutionBackendCreate` | `CourseExecutionBackendGet` |
| `get` | GET | `/course-execution-backends/{id}` | — | `CourseExecutionBackendGet` |
| `list` | GET | `/course-execution-backends` | `CourseExecutionBackendQuery` | `CourseExecutionBackendList[]` |
| `update` | PATCH | `/course-execution-backends/{id}` | `CourseExecutionBackendUpdate` | `CourseExecutionBackendGet` |
| `delete` | DELETE | `/course-execution-backends/{id}` | — | `void` |

## CourseFamilyClient
- Base path: `/course-families`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-families` | `CourseFamilyCreate` | `CourseFamilyGet` |
| `get` | GET | `/course-families/{id}` | — | `CourseFamilyGet` |
| `list` | GET | `/course-families` | `CourseFamilyQuery` | `CourseFamilyList[]` |
| `update` | PATCH | `/course-families/{id}` | `CourseFamilyUpdate` | `CourseFamilyGet` |
| `delete` | DELETE | `/course-families/{id}` | — | `void` |

## CourseGroupClient
- Base path: `/course-groups`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-groups` | `CourseGroupCreate` | `CourseGroupGet` |
| `get` | GET | `/course-groups/{id}` | — | `CourseGroupGet` |
| `list` | GET | `/course-groups` | `CourseGroupQuery` | `CourseGroupList[]` |
| `update` | PATCH | `/course-groups/{id}` | `CourseGroupUpdate` | `CourseGroupGet` |
| `delete` | DELETE | `/course-groups/{id}` | — | `void` |

## CourseClient
- Base path: `/courses`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/courses` | `CourseCreate` | `CourseGet` |
| `get` | GET | `/courses/{id}` | — | `CourseGet` |
| `list` | GET | `/courses` | `CourseQuery` | `CourseList[]` |
| `update` | PATCH | `/courses/{id}` | `CourseUpdate` | `CourseGet` |
| `delete` | DELETE | `/courses/{id}` | — | `void` |

## CourseMemberCommentClient
- Base path: `/course-member-comments`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-member-comments` | `CourseMemberCommentCreate` | `CourseMemberCommentGet` |
| `get` | GET | `/course-member-comments/{id}` | — | `CourseMemberCommentGet` |
| `list` | GET | `/course-member-comments` | `CourseMemberCommentQuery` | `CourseMemberCommentList[]` |
| `update` | PATCH | `/course-member-comments/{id}` | `CourseMemberCommentUpdate` | `CourseMemberCommentGet` |
| `delete` | DELETE | `/course-member-comments/{id}` | — | `void` |

## CourseMemberClient
- Base path: `/course-members`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/course-members` | `CourseMemberCreate` | `CourseMemberGet` |
| `get` | GET | `/course-members/{id}` | — | `CourseMemberGet` |
| `list` | GET | `/course-members` | `CourseMemberQuery` | `CourseMemberList[]` |
| `update` | PATCH | `/course-members/{id}` | `CourseMemberUpdate` | `CourseMemberGet` |
| `delete` | DELETE | `/course-members/{id}` | — | `void` |

## CourseRoleClient
- Base path: `/course-roles`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `get` | GET | `/course-roles/{id}` | — | `CourseRoleGet` |
| `list` | GET | `/course-roles` | `CourseRoleQuery` | `CourseRoleList[]` |

## CourseStudentClient
- Base path: `/student-courses`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `list` | GET | `/student-courses` | `CourseStudentQuery` | `CourseStudentList[]` |

## CourseTutorClient
- Base path: `/tutor-courses`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `list` | GET | `/tutor-courses` | `CourseTutorQuery` | `CourseTutorList[]` |

## DeploymentHistoryClient
- Base path: `/deployment-history`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/deployment-history` | `DeploymentHistoryCreate` | `DeploymentHistoryGet` |
| `get` | GET | `/deployment-history/{id}` | — | `DeploymentHistoryGet` |
| `list` | GET | `/deployment-history` | `ListQuery` | `DeploymentHistoryList[]` |
| `delete` | DELETE | `/deployment-history/{id}` | — | `void` |

## ExampleClient
- Base path: `/examples`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/examples` | `ExampleCreate` | `ExampleGet` |
| `get` | GET | `/examples/{id}` | — | `ExampleGet` |
| `list` | GET | `/examples` | `ExampleQuery` | `ExampleList[]` |
| `update` | PATCH | `/examples/{id}` | `ExampleUpdate` | `ExampleGet` |
| `delete` | DELETE | `/examples/{id}` | — | `void` |

## ExampleRepositoryClient
- Base path: `/example-repositories`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/example-repositories` | `ExampleRepositoryCreate` | `ExampleRepositoryGet` |
| `get` | GET | `/example-repositories/{id}` | — | `ExampleRepositoryGet` |
| `list` | GET | `/example-repositories` | `ExampleRepositoryQuery` | `ExampleRepositoryList[]` |
| `update` | PATCH | `/example-repositories/{id}` | `ExampleRepositoryUpdate` | `ExampleRepositoryGet` |
| `delete` | DELETE | `/example-repositories/{id}` | — | `void` |

## ExecutionBackendClient
- Base path: `/execution-backends`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/execution-backends` | `ExecutionBackendCreate` | `ExecutionBackendGet` |
| `get` | GET | `/execution-backends/{id}` | — | `ExecutionBackendGet` |
| `list` | GET | `/execution-backends` | `ExecutionBackendQuery` | `ExecutionBackendList[]` |
| `update` | PATCH | `/execution-backends/{id}` | `ExecutionBackendUpdate` | `ExecutionBackendGet` |
| `delete` | DELETE | `/execution-backends/{id}` | — | `void` |

## ExtensionClient
- Base path: `/extensions`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/extensions` | `ExtensionPublishRequest` | `ExtensionMetadata` |
| `get` | GET | `/extensions/{id}` | — | `ExtensionMetadata` |
| `list` | GET | `/extensions` | — | `ExtensionVersionListItem[]` |
| `update` | PATCH | `/extensions/{id}` | `ExtensionVersionYankRequest` | `ExtensionMetadata` |
| `delete` | DELETE | `/extensions/{id}` | — | `void` |

## GroupClaimClient
- Base path: `/group-claims`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/group-claims` | `GroupClaimCreate` | `GroupClaimGet` |
| `get` | GET | `/group-claims/{id}` | — | `GroupClaimGet` |
| `list` | GET | `/group-claims` | `GroupClaimQuery` | `GroupClaimList[]` |
| `update` | PATCH | `/group-claims/{id}` | `GroupClaimUpdate` | `GroupClaimGet` |
| `delete` | DELETE | `/group-claims/{id}` | — | `void` |

## GroupClient
- Base path: `/groups`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/groups` | `GroupCreate` | `GroupGet` |
| `get` | GET | `/groups/{id}` | — | `GroupGet` |
| `list` | GET | `/groups` | `GroupQuery` | `GroupList[]` |
| `update` | PATCH | `/groups/{id}` | `GroupUpdate` | `GroupGet` |
| `delete` | DELETE | `/groups/{id}` | — | `void` |

## MessageClient
- Base path: `/messages`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/messages` | `MessageCreate` | `MessageGet` |
| `get` | GET | `/messages/{id}` | — | `MessageGet` |
| `list` | GET | `/messages` | `MessageQuery` | `MessageList[]` |
| `update` | PATCH | `/messages/{id}` | `MessageUpdate` | `MessageGet` |
| `delete` | DELETE | `/messages/{id}` | — | `void` |
| `archive` | PATCH | `/messages/{id}/archive` | — | `void` |

## OrganizationClient
- Base path: `/organizations`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/organizations` | `OrganizationCreate` | `OrganizationGet` |
| `get` | GET | `/organizations/{id}` | — | `OrganizationGet` |
| `list` | GET | `/organizations` | `OrganizationQuery` | `OrganizationList[]` |
| `update` | PATCH | `/organizations/{id}` | `OrganizationUpdate` | `OrganizationGet` |
| `delete` | DELETE | `/organizations/{id}` | — | `void` |
| `archive` | PATCH | `/organizations/{id}/archive` | — | `void` |

## ProfileClient
- Base path: `/profiles`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/profiles` | `ProfileCreate` | `ProfileGet` |
| `get` | GET | `/profiles/{id}` | — | `ProfileGet` |
| `list` | GET | `/profiles` | `ProfileQuery` | `ProfileList[]` |
| `update` | PATCH | `/profiles/{id}` | `ProfileUpdate` | `ProfileGet` |
| `delete` | DELETE | `/profiles/{id}` | — | `void` |

## ResultClient
- Base path: `/results`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/results` | `ResultCreate` | `ResultGet` |
| `get` | GET | `/results/{id}` | — | `ResultGet` |
| `list` | GET | `/results` | `ResultQuery` | `ResultList[]` |
| `update` | PATCH | `/results/{id}` | `ResultUpdate` | `ResultGet` |
| `delete` | DELETE | `/results/{id}` | — | `void` |

## RoleClaimClient
- Base path: `/role-claims`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `get` | GET | `/role-claims/{id}` | — | `RoleClaimGet` |
| `list` | GET | `/role-claims` | `RoleClaimQuery` | `RoleClaimList[]` |

## RoleClient
- Base path: `/roles`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `get` | GET | `/roles/{id}` | — | `RoleGet` |
| `list` | GET | `/roles` | `RoleQuery` | `RoleList[]` |

## SessionClient
- Base path: `/sessions`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/sessions` | `SessionCreate` | `SessionGet` |
| `get` | GET | `/sessions/{id}` | — | `SessionGet` |
| `list` | GET | `/sessions` | `SessionQuery` | `SessionList[]` |
| `update` | PATCH | `/sessions/{id}` | `SessionUpdate` | `SessionGet` |
| `delete` | DELETE | `/sessions/{id}` | — | `void` |

## StorageClient
- Base path: `/storage`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/storage` | `StorageObjectCreate` | `StorageObjectGet` |
| `get` | GET | `/storage/{id}` | — | `StorageObjectGet` |
| `list` | GET | `/storage` | `StorageObjectQuery` | `StorageObjectList[]` |
| `update` | PATCH | `/storage/{id}` | `StorageObjectUpdate` | `StorageObjectGet` |
| `delete` | DELETE | `/storage/{id}` | — | `void` |

## StudentProfileClient
- Base path: `/student-profiles`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/student-profiles` | `StudentProfileCreate` | `StudentProfileGet` |
| `get` | GET | `/student-profiles/{id}` | — | `StudentProfileGet` |
| `list` | GET | `/student-profiles` | `StudentProfileQuery` | `StudentProfileList[]` |
| `update` | PATCH | `/student-profiles/{id}` | `StudentProfileUpdate` | `StudentProfileGet` |
| `delete` | DELETE | `/student-profiles/{id}` | — | `void` |

## SubmissionGroupGradingClient
- Base path: `/submission-group-gradings`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/submission-group-gradings` | `SubmissionGroupGradingCreate` | `SubmissionGroupGradingGet` |
| `get` | GET | `/submission-group-gradings/{id}` | — | `SubmissionGroupGradingGet` |
| `list` | GET | `/submission-group-gradings` | `SubmissionGroupGradingQuery` | `SubmissionGroupGradingList[]` |
| `update` | PATCH | `/submission-group-gradings/{id}` | `SubmissionGroupGradingUpdate` | `SubmissionGroupGradingGet` |
| `delete` | DELETE | `/submission-group-gradings/{id}` | — | `void` |

## SubmissionGroupClient
- Base path: `/submission-groups`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/submission-groups` | `SubmissionGroupCreate` | `SubmissionGroupGet` |
| `get` | GET | `/submission-groups/{id}` | — | `SubmissionGroupGet` |
| `list` | GET | `/submission-groups` | `SubmissionGroupQuery` | `SubmissionGroupList[]` |
| `update` | PATCH | `/submission-groups/{id}` | `SubmissionGroupUpdate` | `SubmissionGroupGet` |
| `delete` | DELETE | `/submission-groups/{id}` | — | `void` |

## SubmissionGroupMemberClient
- Base path: `/submission-group-members`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/submission-group-members` | `SubmissionGroupMemberCreate` | `SubmissionGroupMemberGet` |
| `get` | GET | `/submission-group-members/{id}` | — | `SubmissionGroupMemberGet` |
| `list` | GET | `/submission-group-members` | `SubmissionGroupMemberQuery` | `SubmissionGroupMemberList[]` |
| `update` | PATCH | `/submission-group-members/{id}` | `SubmissionGroupMemberUpdate` | `SubmissionGroupMemberGet` |
| `delete` | DELETE | `/submission-group-members/{id}` | — | `void` |

## UserGroupClient
- Base path: `/user-groups`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/user-groups` | `UserGroupCreate` | `UserGroupGet` |
| `get` | GET | `/user-groups/{id}` | — | `UserGroupGet` |
| `list` | GET | `/user-groups` | `UserGroupQuery` | `UserGroupList[]` |
| `update` | PATCH | `/user-groups/{id}` | `UserGroupUpdate` | `UserGroupGet` |
| `delete` | DELETE | `/user-groups/{id}` | — | `void` |

## UserClient
- Base path: `/users`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/users` | `UserCreate` | `UserGet` |
| `get` | GET | `/users/{id}` | — | `UserGet` |
| `list` | GET | `/users` | `UserQuery` | `UserList[]` |
| `update` | PATCH | `/users/{id}` | `UserUpdate` | `UserGet` |
| `delete` | DELETE | `/users/{id}` | — | `void` |
| `archive` | PATCH | `/users/{id}/archive` | — | `void` |

## UserRoleClient
- Base path: `/user-roles`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/user-roles` | `UserRoleCreate` | `UserRoleGet` |
| `get` | GET | `/user-roles/{id}` | — | `UserRoleGet` |
| `list` | GET | `/user-roles` | `UserRoleQuery` | `UserRoleList[]` |
| `update` | PATCH | `/user-roles/{id}` | `UserRoleUpdate` | `UserRoleGet` |
| `delete` | DELETE | `/user-roles/{id}` | — | `void` |
