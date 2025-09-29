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
| `getCourseContentMetaCourseContentsFilesCourseContentIdGet` | GET | `/course-contents/files/{course_content_id}` | — | `Record<string, unknown> & Record<string, unknown>` |
| `assignExampleToContentCourseContentsContentIdAssignExamplePost` | POST | `/course-contents/{content_id}/assign-example` | `AssignExampleRequest` | `DeploymentWithHistory` |
| `unassignExampleFromContentCourseContentsContentIdExampleDelete` | DELETE | `/course-contents/{content_id}/example` | — | `Record<string, unknown> & Record<string, string>` |
| `getDeploymentStatusWithWorkflowCourseContentsDeploymentContentIdGet` | GET | `/course-contents/deployment/{content_id}` | — | `Record<string, unknown> & Record<string, unknown>` |
| `getCourseDeploymentSummaryCourseContentsCoursesCourseIdDeploymentSummaryGet` | GET | `/course-contents/courses/{course_id}/deployment-summary` | — | `DeploymentSummary` |
| `getContentDeploymentCourseContentsContentIdDeploymentGet` | GET | `/course-contents/{content_id}/deployment` | — | `DeploymentWithHistory | null` |

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
| `patchCourseExecutionBackendCoursesCourseIdExecutionBackendsExecutionBackendIdPatch` | PATCH | `/courses/{course_id}/execution-backends/{execution_backend_id}` | `Record<string, unknown> & Record<string, unknown>` | `CourseExecutionBackendGet` |
| `deleteCourseExecutionBackendCoursesCourseIdExecutionBackendsExecutionBackendIdDelete` | DELETE | `/courses/{course_id}/execution-backends/{execution_backend_id}` | — | `Record<string, unknown> & Record<string, unknown>` |

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
| `createVersionExamplesExampleIdVersionsPost` | POST | `/examples/{example_id}/versions` | `ExampleVersionCreate` | `ExampleVersionGet` |
| `listVersionsExamplesExampleIdVersionsGet` | GET | `/examples/{example_id}/versions` | — | `ExampleVersionList[]` |
| `getVersionExamplesVersionsVersionIdGet` | GET | `/examples/versions/{version_id}` | — | `ExampleVersionGet` |
| `createExampleDependencyExamplesExampleIdDependenciesPost` | POST | `/examples/{example_id}/dependencies` | `ExampleDependencyCreate` | `ExampleDependencyGet` |
| `getExampleDependenciesExamplesExampleIdDependenciesGet` | GET | `/examples/{example_id}/dependencies` | — | `ExampleDependencyGet[]` |
| `removeDependencyExamplesDependenciesDependencyIdDelete` | DELETE | `/examples/dependencies/{dependency_id}` | — | `void` |
| `uploadExampleExamplesUploadPost` | POST | `/examples/upload` | `ExampleUploadRequest` | `ExampleVersionGet` |
| `downloadExampleLatestExamplesExampleIdDownloadGet` | GET | `/examples/{example_id}/download` | — | `ExampleDownloadResponse` |
| `downloadExampleVersionExamplesDownloadVersionIdGet` | GET | `/examples/download/{version_id}` | — | `ExampleDownloadResponse` |
| `deleteExampleDependencyExamplesExampleIdDependenciesDependencyIdDelete` | DELETE | `/examples/{example_id}/dependencies/{dependency_id}` | — | `void` |

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
| `publishExtensionVersionExtensionsExtensionIdentityVersionsPost` | POST | `/extensions/{extension_identity}/versions` | — | `ExtensionPublishResponse` |
| `listExtensionVersionsExtensionsExtensionIdentityVersionsGet` | GET | `/extensions/{extension_identity}/versions` | — | `ExtensionVersionListResponse` |
| `downloadExtensionExtensionsExtensionIdentityDownloadGet` | GET | `/extensions/{extension_identity}/download` | — | `void` |
| `updateExtensionVersionExtensionsExtensionIdentityVersionsVersionPatch` | PATCH | `/extensions/{extension_identity}/versions/{version}` | `ExtensionVersionYankRequest` | `ExtensionVersionDetail` |

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
| `markMessageReadMessagesIdReadsPost` | POST | `/messages/{id}/reads` | — | `void` |
| `markMessageUnreadMessagesIdReadsDelete` | DELETE | `/messages/{id}/reads` | — | `void` |

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
| `patchOrganizationsTokenOrganizationsOrganizationIdTokenPatch` | PATCH | `/organizations/{organization_id}/token` | `OrganizationUpdateTokenUpdate` | `void` |

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
| `resultStatusResultsResultIdStatusGet` | GET | `/results/{result_id}/status` | — | `TaskStatus` |

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
| `uploadFileStorageUploadPost` | POST | `/storage/upload` | — | `StorageObjectGet` |
| `downloadFileStorageDownloadObjectKeyGet` | GET | `/storage/download/{object_key}` | — | `void` |
| `listObjectsStorageObjectsGet` | GET | `/storage/objects` | — | `StorageObjectList[]` |
| `getObjectInfoStorageObjectsObjectKeyGet` | GET | `/storage/objects/{object_key}` | — | `StorageObjectGet` |
| `deleteObjectStorageObjectsObjectKeyDelete` | DELETE | `/storage/objects/{object_key}` | — | `void` |
| `copyObjectStorageCopyPost` | POST | `/storage/copy` | — | `void` |
| `generatePresignedUrlStoragePresignedUrlPost` | POST | `/storage/presigned-url` | `PresignedUrlRequest` | `PresignedUrlResponse` |
| `listBucketsStorageBucketsGet` | GET | `/storage/buckets` | — | `BucketInfo[]` |
| `createBucketStorageBucketsPost` | POST | `/storage/buckets` | `BucketCreate` | `BucketInfo` |
| `deleteBucketStorageBucketsBucketNameDelete` | DELETE | `/storage/buckets/{bucket_name}` | — | `void` |
| `getBucketStatsStorageBucketsBucketNameStatsGet` | GET | `/storage/buckets/{bucket_name}/stats` | — | `StorageUsageStats` |

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
| `getUserRoleUserRolesUsersUserIdRolesRoleIdGet` | GET | `/user-roles/users/{user_id}/roles/{role_id}` | — | `UserRoleGet` |
| `deleteUserRoleUserRolesUsersUserIdRolesRoleIdDelete` | DELETE | `/user-roles/users/{user_id}/roles/{role_id}` | — | `UserRoleList[]` |

## SystemClient
- Base path: `/system`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `createOrganizationAsyncSystemDeployOrganizationsPost` | POST | `/system/deploy/organizations` | `OrganizationTaskRequest` | `TaskResponse` |
| `createCourseFamilyAsyncSystemDeployCourseFamiliesPost` | POST | `/system/deploy/course-families` | `CourseFamilyTaskRequest` | `TaskResponse` |
| `createCourseAsyncSystemDeployCoursesPost` | POST | `/system/deploy/courses` | `CourseTaskRequest` | `TaskResponse` |
| `generateStudentTemplateSystemCoursesCourseIdGenerateStudentTemplatePost` | POST | `/system/courses/{course_id}/generate-student-template` | `GenerateTemplateRequest` | `GenerateTemplateResponse` |
| `generateAssignmentsSystemCoursesCourseIdGenerateAssignmentsPost` | POST | `/system/courses/{course_id}/generate-assignments` | `GenerateAssignmentsRequest` | `GenerateAssignmentsResponse` |
| `getCourseGitlabStatusSystemCoursesCourseIdGitlabStatusGet` | GET | `/system/courses/{course_id}/gitlab-status` | — | `Record<string, unknown> & Record<string, unknown>` |
| `createHierarchySystemHierarchyCreatePost` | POST | `/system/hierarchy/create` | `Record<string, unknown> & Record<string, unknown>` | `Record<string, unknown> & Record<string, unknown>` |
| `getHierarchyStatusSystemHierarchyStatusWorkflowIdGet` | GET | `/system/hierarchy/status/{workflow_id}` | — | `Record<string, unknown> & Record<string, unknown>` |

## TestsClient
- Base path: `/tests`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `createTestForArtifactTestsArtifactsArtifactIdTestPost` | POST | `/tests/artifacts/{artifact_id}/test` | `TestCreate` | `ResultList` |
| `getTestStatusTestsTestResultsTestIdStatusGet` | GET | `/tests/test-results/{test_id}/status` | — | `void` |
| `createTestLegacyTestsLegacyPost` | POST | `/tests/legacy` | `TestCreate` | `ResultList` |

## StudentsClient
- Base path: `/students`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `studentGetCourseContentStudentsCourseContentsCourseContentIdGet` | GET | `/students/course-contents/{course_content_id}` | — | `CourseContentStudentGet` |
| `studentListCourseContentsStudentsCourseContentsGet` | GET | `/students/course-contents` | — | `CourseContentStudentList[]` |
| `studentListCoursesStudentsCoursesGet` | GET | `/students/courses` | — | `CourseStudentList[]` |
| `studentGetCourseStudentsCoursesCourseIdGet` | GET | `/students/courses/{course_id}` | — | `CourseStudentGet` |
| `getSignupInitDataStudentsRepositoriesGet` | GET | `/students/repositories` | — | `string[]` |

## TutorsClient
- Base path: `/tutors`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `tutorGetCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdGet` | GET | `/tutors/course-members/{course_member_id}/course-contents/{course_content_id}` | — | `CourseContentStudentGet` |
| `tutorUpdateCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdPatch` | PATCH | `/tutors/course-members/{course_member_id}/course-contents/{course_content_id}` | `CourseContentStudentUpdate` | `CourseContentStudentList` |
| `tutorListCourseContentsTutorsCourseMembersCourseMemberIdCourseContentsGet` | GET | `/tutors/course-members/{course_member_id}/course-contents` | — | `CourseContentStudentList[]` |
| `tutorGetCoursesTutorsCoursesCourseIdGet` | GET | `/tutors/courses/{course_id}` | — | `CourseTutorGet` |
| `tutorListCoursesTutorsCoursesGet` | GET | `/tutors/courses` | — | `CourseTutorList[]` |
| `tutorGetCourseMembersTutorsCourseMembersCourseMemberIdGet` | GET | `/tutors/course-members/{course_member_id}` | — | `TutorCourseMemberGet` |
| `tutorListCourseMembersTutorsCourseMembersGet` | GET | `/tutors/course-members` | — | `TutorCourseMemberList[]` |

## LecturersClient
- Base path: `/lecturers`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `lecturerGetCoursesLecturersCoursesCourseIdGet` | GET | `/lecturers/courses/{course_id}` | — | `CourseGet` |
| `lecturerListCoursesLecturersCoursesGet` | GET | `/lecturers/courses` | — | `CourseList[]` |

## SignupClient
- Base path: `/signup`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `gitlabSignupSignupGitlabPost` | POST | `/signup/gitlab` | `GitlabSignup` | `GitlabSignupResponse` |

## UserClient
- Base path: `/user`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getCurrentUserUserGet` | GET | `/user` | — | `UserGet` |
| `setUserPasswordUserPasswordPost` | POST | `/user/password` | `UserPassword` | `void` |
| `getCourseViewsForCurrentUserUserCoursesCourseIdViewsGet` | GET | `/user/courses/{course_id}/views` | — | `string[]` |
| `validateCurrentUserCourseUserCoursesCourseIdValidatePost` | POST | `/user/courses/{course_id}/validate` | `CourseMemberValidationRequest` | `CourseMemberReadinessStatus` |
| `registerCurrentUserCourseAccountUserCoursesCourseIdRegisterPost` | POST | `/user/courses/{course_id}/register` | `CourseMemberProviderAccountUpdate` | `CourseMemberReadinessStatus` |

## InfoClient
- Base path: `/info`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getServerInfoInfoGet` | GET | `/info` | — | `Record<string, unknown> & Record<string, unknown>` |

## TasksClient
- Base path: `/tasks`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listTasksTasksGet` | GET | `/tasks` | — | `Record<string, unknown> & Record<string, unknown>` |
| `submitTaskTasksSubmitPost` | POST | `/tasks/submit` | `TaskSubmission` | `Record<string, unknown> & Record<string, string>` |
| `getTaskTasksTaskIdGet` | GET | `/tasks/{task_id}` | — | `TaskInfo` |
| `deleteTaskTasksTaskIdDelete` | DELETE | `/tasks/{task_id}` | — | `void` |
| `getTaskStatusTasksTaskIdStatusGet` | GET | `/tasks/{task_id}/status` | — | `TaskInfo` |
| `getTaskResultTasksTaskIdResultGet` | GET | `/tasks/{task_id}/result` | — | `TaskResult` |
| `cancelTaskTasksTaskIdCancelDelete` | DELETE | `/tasks/{task_id}/cancel` | — | `void` |
| `listTaskTypesTasksTypesGet` | GET | `/tasks/types` | — | `string[]` |
| `getWorkerStatusTasksWorkersStatusGet` | GET | `/tasks/workers/status` | — | `Record<string, unknown> & Record<string, unknown>` |

## SsoClient
- Base path: `/auth`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listProvidersAuthProvidersGet` | GET | `/auth/providers` | — | `ProviderInfo[]` |
| `initiateLoginAuthProviderLoginGet` | GET | `/auth/{provider}/login` | — | `void` |
| `handleCallbackAuthProviderCallbackGet` | GET | `/auth/{provider}/callback` | — | `void` |
| `ssoSuccessAuthSuccessGet` | GET | `/auth/success` | — | `void` |
| `getCurrentUserInfoAuthMeGet` | GET | `/auth/me` | — | `void` |
| `logoutAuthProviderLogoutPost` | POST | `/auth/{provider}/logout` | — | `void` |
| `listAllPluginsAuthAdminPluginsGet` | GET | `/auth/admin/plugins` | — | `void` |
| `enablePluginAuthAdminPluginsPluginNameEnablePost` | POST | `/auth/admin/plugins/{plugin_name}/enable` | — | `void` |
| `disablePluginAuthAdminPluginsPluginNameDisablePost` | POST | `/auth/admin/plugins/{plugin_name}/disable` | — | `void` |
| `reloadPluginsAuthAdminPluginsReloadPost` | POST | `/auth/admin/plugins/reload` | — | `void` |
| `registerUserAuthRegisterPost` | POST | `/auth/register` | `UserRegistrationRequest` | `UserRegistrationResponse` |
| `refreshTokenAuthRefreshPost` | POST | `/auth/refresh` | `TokenRefreshRequest` | `TokenRefreshResponse` |

## SubmissionsClient
- Base path: `/submissions`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listSubmissionsSubmissionsGet` | GET | `/submissions` | — | `unknown[]` |
| `uploadSubmissionSubmissionsPost` | POST | `/submissions` | — | `SubmissionUploadResponseModel` |

## ArtifactsClient
- Base path: `/artifacts`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `createArtifactGradeArtifactsArtifactIdGradesPost` | POST | `/artifacts/{artifact_id}/grades` | `SubmissionGradeCreate` | `SubmissionGradeDetail` |
| `listArtifactGradesArtifactsArtifactIdGradesGet` | GET | `/artifacts/{artifact_id}/grades` | — | `SubmissionGradeListItem[]` |
| `updateArtifactGradeArtifactsGradesGradeIdPatch` | PATCH | `/artifacts/grades/{grade_id}` | `SubmissionGradeUpdate` | `SubmissionGradeDetail` |
| `deleteArtifactGradeArtifactsGradesGradeIdDelete` | DELETE | `/artifacts/grades/{grade_id}` | — | `void` |
| `createArtifactReviewArtifactsArtifactIdReviewsPost` | POST | `/artifacts/{artifact_id}/reviews` | `SubmissionReviewCreate` | `SubmissionReviewListItem` |
| `listArtifactReviewsArtifactsArtifactIdReviewsGet` | GET | `/artifacts/{artifact_id}/reviews` | — | `SubmissionReviewListItem[]` |
| `updateArtifactReviewArtifactsReviewsReviewIdPatch` | PATCH | `/artifacts/reviews/{review_id}` | `SubmissionReviewUpdate` | `SubmissionReviewListItem` |
| `deleteArtifactReviewArtifactsReviewsReviewIdDelete` | DELETE | `/artifacts/reviews/{review_id}` | — | `void` |
| `createTestResultArtifactsArtifactIdTestPost` | POST | `/artifacts/{artifact_id}/test` | `ResultCreate` | `ResultList` |
| `listArtifactTestResultsArtifactsArtifactIdTestsGet` | GET | `/artifacts/{artifact_id}/tests` | — | `ResultList[]` |
| `updateTestResultArtifactsTestsTestIdPatch` | PATCH | `/artifacts/tests/{test_id}` | `ResultUpdate` | `ResultList` |

## MiscClient
- Base path: `/`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getStatusHeadHead` | HEAD | `/` | — | `void` |
