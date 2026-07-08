# API Client Endpoint Summary

## InviteLinkClient
- Base path: `/admin/invites`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `create` | POST | `/admin/invites` | `InviteLinkCreate` | `InviteLinkGet` |
| `get` | GET | `/admin/invites/{id}` | — | `InviteLinkGet` |
| `list` | GET | `/admin/invites` | — | `InviteLinkList[]` |
| `delete` | DELETE | `/admin/invites/{id}` | — | `void` |

## RoleClaimClient
- Base path: `/role-claims`

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `get` | GET | `/role-claims/{id}` | — | `RoleClaimGet` |
| `list` | GET | `/role-claims` | `RoleClaimQuery` | `RoleClaimList[]` |

## AccountsClient
- Base path: `/accounts`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listAccountsAccountsGet` | GET | `/accounts` | — | `AccountList[]` |
| `createAccountsAccountsPost` | POST | `/accounts` | `AccountCreate` | `AccountGet` |
| `listAccountProvidersAccountsProvidersGet` | GET | `/accounts/providers` | — | `AccountProvider[]` |
| `deleteAccountsAccountsIdDelete` | DELETE | `/accounts/{id}` | — | `void` |
| `getAccountsAccountsIdGet` | GET | `/accounts/{id}` | — | `AccountGet` |
| `updateAccountsAccountsIdPatch` | PATCH | `/accounts/{id}` | `AccountUpdate` | `AccountGet` |

## AuthenticationClient
- Base path: `/auth`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listAllPluginsAuthAdminPluginsGet` | GET | `/auth/admin/plugins` | — | `Record<string, unknown> & Record<string, unknown>` |
| `reloadPluginsAuthAdminPluginsReloadPost` | POST | `/auth/admin/plugins/reload` | — | `Record<string, unknown> & Record<string, unknown>` |
| `disablePluginAuthAdminPluginsPluginNameDisablePost` | POST | `/auth/admin/plugins/{plugin_name}/disable` | — | `Record<string, unknown> & Record<string, unknown>` |
| `enablePluginAuthAdminPluginsPluginNameEnablePost` | POST | `/auth/admin/plugins/{plugin_name}/enable` | — | `Record<string, unknown> & Record<string, unknown>` |
| `logoutAuthLogoutPost` | POST | `/auth/logout` | — | `LogoutResponse` |
| `listProvidersAuthProvidersGet` | GET | `/auth/providers` | — | `ProviderInfo[]` |
| `refreshTokenAuthRefreshPost` | POST | `/auth/refresh` | `TokenRefreshRequest` | `TokenRefreshResponse` |
| `refreshLocalTokenAuthRefreshLocalPost` | POST | `/auth/refresh/local` | `LocalTokenRefreshRequest` | `LocalTokenRefreshResponse` |
| `ssoSuccessAuthSuccessGet` | GET | `/auth/success` | — | `void` |
| `verifyCoderAccessAuthVerifyCoderAccessGet` | GET | `/auth/verify-coder-access` | — | `void` |
| `handleCallbackAuthProviderCallbackGet` | GET | `/auth/{provider}/callback` | — | `void` |
| `initiateLoginAuthProviderLoginGet` | GET | `/auth/{provider}/login` | — | `void` |
| `ssoLogoutAuthProviderLogoutGet` | GET | `/auth/{provider}/logout` | — | `void` |

## ConsentClient
- Base path: `/consent`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `giveConsentConsentPost` | POST | `/consent` | `ConsentCreate` | `ConsentStatusGet` |
| `getPolicyTextConsentPolicyGet` | GET | `/consent/policy` | — | `PolicyTextGet` |
| `listPolicyVersionsConsentPolicyVersionsGet` | GET | `/consent/policy-versions` | — | `PolicyVersionGet[]` |
| `publishPolicyVersionConsentPolicyVersionsPost` | POST | `/consent/policy-versions` | `PolicyVersionCreate` | `PolicyVersionGet` |
| `getConsentStatusConsentStatusGet` | GET | `/consent/status` | — | `ConsentStatusGet` |
| `withdrawConsentConsentWithdrawPost` | POST | `/consent/withdraw` | — | `ConsentStatusGet` |

## CourseContentKindsClient
- Base path: `/course-content-kinds`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseContentKindsCourseContentKindsGet` | GET | `/course-content-kinds` | — | `CourseContentKindList[]` |
| `createCourseContentKindsCourseContentKindsPost` | POST | `/course-content-kinds` | `CourseContentKindCreate` | `CourseContentKindGet` |
| `deleteCourseContentKindsCourseContentKindsIdDelete` | DELETE | `/course-content-kinds/{id}` | — | `void` |
| `getCourseContentKindsCourseContentKindsIdGet` | GET | `/course-content-kinds/{id}` | — | `CourseContentKindGet` |
| `updateCourseContentKindsCourseContentKindsIdPatch` | PATCH | `/course-content-kinds/{id}` | `CourseContentKindUpdate` | `CourseContentKindGet` |

## CourseContentTypesClient
- Base path: `/course-content-types`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseContentTypesCourseContentTypesGet` | GET | `/course-content-types` | — | `CourseContentTypeList[]` |
| `createCourseContentTypesCourseContentTypesPost` | POST | `/course-content-types` | `CourseContentTypeCreate` | `CourseContentTypeGet` |
| `deleteCourseContentTypesCourseContentTypesIdDelete` | DELETE | `/course-content-types/{id}` | — | `void` |
| `getCourseContentTypesCourseContentTypesIdGet` | GET | `/course-content-types/{id}` | — | `CourseContentTypeGet` |
| `updateCourseContentTypesCourseContentTypesIdPatch` | PATCH | `/course-content-types/{id}` | `CourseContentTypeUpdate` | `CourseContentTypeGet` |

## CourseContentsClient
- Base path: `/course-contents`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseContentsCourseContentsGet` | GET | `/course-contents` | — | `CourseContentList[]` |
| `createCourseContentsCourseContentsPost` | POST | `/course-contents` | `CourseContentCreate` | `CourseContentGet` |
| `getCourseDeploymentSummaryCourseContentsCoursesCourseIdDeploymentSummaryGet` | GET | `/course-contents/courses/{course_id}/deployment-summary` | — | `DeploymentSummary` |
| `getDeploymentStatusWithWorkflowCourseContentsDeploymentContentIdGet` | GET | `/course-contents/deployment/{content_id}` | — | `Record<string, unknown> & Record<string, unknown>` |
| `getContentDeploymentCourseContentsContentIdDeploymentGet` | GET | `/course-contents/{content_id}/deployment` | — | `DeploymentWithHistory | null` |
| `unassignExampleFromContentCourseContentsContentIdExampleDelete` | DELETE | `/course-contents/{content_id}/example` | — | `Record<string, unknown> & Record<string, string>` |
| `moveCourseContentCourseContentsContentIdMovePatch` | PATCH | `/course-contents/{content_id}/move` | `CourseContentMoveRequest` | `CourseContentGet` |
| `deleteCourseContentsCourseContentsIdDelete` | DELETE | `/course-contents/{id}` | — | `void` |
| `getCourseContentsCourseContentsIdGet` | GET | `/course-contents/{id}` | — | `CourseContentGet` |
| `updateCourseContentsCourseContentsIdPatch` | PATCH | `/course-contents/{id}` | `CourseContentUpdate` | `CourseContentGet` |
| `routeCourseContentsCourseContentsIdArchivePatch` | PATCH | `/course-contents/{id}/archive` | — | `void` |
| `unarchiveCourseContentsCourseContentsIdUnarchivePatch` | PATCH | `/course-contents/{id}/unarchive` | — | `void` |

## CourseFamiliesClient
- Base path: `/course-families`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseFamiliesCourseFamiliesGet` | GET | `/course-families` | — | `CourseFamilyList[]` |
| `createCourseFamiliesCourseFamiliesPost` | POST | `/course-families` | `CourseFamilyCreate` | `CourseFamilyGet` |
| `deleteCourseFamilyEndpointCourseFamiliesCourseFamilyIdDelete` | DELETE | `/course-families/{course_family_id}` | — | `CascadeDeleteResult` |
| `deployCourseCourseFamiliesCourseFamilyIdDeployCoursePost` | POST | `/course-families/{course_family_id}/deploy-course` | `CourseDeployRequest` | `CourseDeployResult` |
| `deleteCourseFamiliesCourseFamiliesIdDelete` | DELETE | `/course-families/{id}` | — | `void` |
| `getCourseFamiliesCourseFamiliesIdGet` | GET | `/course-families/{id}` | — | `CourseFamilyGet` |
| `updateCourseFamiliesCourseFamiliesIdPatch` | PATCH | `/course-families/{id}` | `CourseFamilyUpdate` | `CourseFamilyGet` |

## CourseFamilyMembersClient
- Base path: `/course-family-members`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseFamilyMembersCourseFamilyMembersGet` | GET | `/course-family-members` | — | `CourseFamilyMemberList[]` |
| `createCourseFamilyMembersCourseFamilyMembersPost` | POST | `/course-family-members` | `CourseFamilyMemberCreate` | `CourseFamilyMemberGet` |
| `deleteCourseFamilyMembersCourseFamilyMembersIdDelete` | DELETE | `/course-family-members/{id}` | — | `void` |
| `getCourseFamilyMembersCourseFamilyMembersIdGet` | GET | `/course-family-members/{id}` | — | `CourseFamilyMemberGet` |
| `updateCourseFamilyMembersCourseFamilyMembersIdPatch` | PATCH | `/course-family-members/{id}` | `CourseFamilyMemberUpdate` | `CourseFamilyMemberGet` |

## CourseFamilyRolesClient
- Base path: `/course-family-roles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseFamilyRolesCourseFamilyRolesGet` | GET | `/course-family-roles` | — | `CourseFamilyRoleList[]` |
| `getCourseFamilyRolesCourseFamilyRolesIdGet` | GET | `/course-family-roles/{id}` | — | `CourseFamilyRoleGet` |

## CourseGroupsClient
- Base path: `/course-groups`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseGroupsCourseGroupsGet` | GET | `/course-groups` | — | `CourseGroupList[]` |
| `createCourseGroupsCourseGroupsPost` | POST | `/course-groups` | `CourseGroupCreate` | `CourseGroupGet` |
| `deleteCourseGroupsCourseGroupsIdDelete` | DELETE | `/course-groups/{id}` | — | `void` |
| `getCourseGroupsCourseGroupsIdGet` | GET | `/course-groups/{id}` | — | `CourseGroupGet` |
| `updateCourseGroupsCourseGroupsIdPatch` | PATCH | `/course-groups/{id}` | `CourseGroupUpdate` | `CourseGroupGet` |

## CourseMemberCommentsClient
- Base path: `/course-member-comments`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCommentsCourseMemberCommentsGet` | GET | `/course-member-comments` | — | `CourseMemberCommentList[]` |
| `createCommentCourseMemberCommentsPost` | POST | `/course-member-comments` | `CommentCreate` | `CourseMemberCommentList[]` |
| `deleteCommentCourseMemberCommentsCourseMemberCommentIdDelete` | DELETE | `/course-member-comments/{course_member_comment_id}` | — | `CourseMemberCommentList[]` |
| `updateCommentCourseMemberCommentsCourseMemberCommentIdPatch` | PATCH | `/course-member-comments/{course_member_comment_id}` | `CommentUpdate` | `CourseMemberCommentList[]` |

## CourseMemberGradingsClient
- Base path: `/course-member-gradings`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseMemberGradingsEndpointCourseMemberGradingsGet` | GET | `/course-member-gradings` | — | `CourseMemberGradingsList[]` |
| `getCourseMemberGradingsEndpointCourseMemberGradingsCourseMemberIdGet` | GET | `/course-member-gradings/{course_member_id}` | — | `CourseMemberGradingsGet` |

## CourseMemberImportClient
- Base path: `/course-member-import`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `parseMemberFileCourseMemberImportParseCourseIdPost` | POST | `/course-member-import/parse/{course_id}` | `CourseMemberImportFileParseRequest` | `CourseMemberImportParseResponse` |
| `importMemberCourseMemberImportCourseIdPost` | POST | `/course-member-import/{course_id}` | `CourseMemberImportRequest` | `CourseMemberImportResponse` |

## CourseMembersClient
- Base path: `/course-members`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseMembersCourseMembersGet` | GET | `/course-members` | — | `CourseMemberList[]` |
| `createCourseMembersCourseMembersPost` | POST | `/course-members` | `CourseMemberCreate` | `CourseMemberGet` |
| `deleteCourseMembersCourseMembersIdDelete` | DELETE | `/course-members/{id}` | — | `void` |
| `getCourseMembersCourseMembersIdGet` | GET | `/course-members/{id}` | — | `CourseMemberGet` |
| `updateCourseMembersCourseMembersIdPatch` | PATCH | `/course-members/{id}` | `CourseMemberUpdate` | `CourseMemberGet` |

## CourseRolesClient
- Base path: `/course-roles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCourseRolesCourseRolesGet` | GET | `/course-roles` | — | `CourseRoleList[]` |
| `getCourseRolesCourseRolesIdGet` | GET | `/course-roles/{id}` | — | `CourseRoleGet` |

## CoursesClient
- Base path: `/courses`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listCoursesCoursesGet` | GET | `/courses` | — | `CourseList[]` |
| `createCoursesCoursesPost` | POST | `/courses` | `CourseCreate` | `CourseGet` |
| `deleteCourseEndpointCoursesCourseIdDelete` | DELETE | `/courses/{course_id}` | — | `CascadeDeleteResult` |
| `getCourseGitBindingEndpointCoursesCourseIdGitGet` | GET | `/courses/{course_id}/git` | — | `CourseGitBindingGet` |
| `upsertCourseGitBindingEndpointCoursesCourseIdGitPut` | PUT | `/courses/{course_id}/git` | `CourseGitBindingUpsert` | `CourseGitBindingGet` |
| `deleteCoursesCoursesIdDelete` | DELETE | `/courses/{id}` | — | `void` |
| `getCoursesCoursesIdGet` | GET | `/courses/{id}` | — | `CourseGet` |
| `updateCoursesCoursesIdPatch` | PATCH | `/courses/{id}` | `CourseUpdate` | `CourseGet` |

## DocumentsClient
- Base path: `/documents`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `deleteDocumentDirectoryDocumentsDirectoriesDelete` | DELETE | `/documents/directories` | `DocumentDirectoryDelete` | `void` |
| `renameDocumentDirectoryDocumentsDirectoriesPatch` | PATCH | `/documents/directories` | `DocumentDirectoryRename` | `DocumentDirectoryGet` |
| `createDocumentDirectoryDocumentsDirectoriesPost` | POST | `/documents/directories` | `DocumentDirectoryCreate` | `DocumentDirectoryGet` |
| `deleteDocumentFileDocumentsFilesDelete` | DELETE | `/documents/files` | `DocumentDelete` | `void` |
| `getDocumentFileDocumentsFilesGet` | GET | `/documents/files` | — | `void` |
| `renameDocumentFileDocumentsFilesPatch` | PATCH | `/documents/files` | `DocumentRename` | `DocumentGet` |
| `uploadDocumentFileDocumentsFilesPost` | POST | `/documents/files` | — | `DocumentGet` |
| `listDocumentsDirectoryDocumentsListGet` | GET | `/documents/list` | — | `DocumentList[]` |

## ExampleRepositoriesClient
- Base path: `/example-repositories`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listExampleRepositoriesExampleRepositoriesGet` | GET | `/example-repositories` | — | `ExampleRepositoryList[]` |
| `createExampleRepositoriesExampleRepositoriesPost` | POST | `/example-repositories` | `ExampleRepositoryCreate` | `ExampleRepositoryGet` |
| `deleteExampleRepositoriesExampleRepositoriesIdDelete` | DELETE | `/example-repositories/{id}` | — | `void` |
| `getExampleRepositoriesExampleRepositoriesIdGet` | GET | `/example-repositories/{id}` | — | `ExampleRepositoryGet` |
| `updateExampleRepositoriesExampleRepositoriesIdPatch` | PATCH | `/example-repositories/{id}` | `ExampleRepositoryUpdate` | `ExampleRepositoryGet` |

## ExamplesClient
- Base path: `/examples`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listExamplesExamplesGet` | GET | `/examples` | — | `ExampleList[]` |
| `deleteExamplesByPatternEndpointExamplesByPatternDelete` | DELETE | `/examples/by-pattern` | — | `ExampleBulkDeleteResult` |
| `downloadExampleVersionExamplesDownloadVersionIdGet` | GET | `/examples/download/{version_id}` | — | `ExampleDownloadResponse` |
| `uploadExampleExamplesUploadPost` | POST | `/examples/upload` | `ExampleUploadRequest` | `ExampleVersionGet` |
| `deleteExampleVersionEndpointExamplesVersionsVersionIdDelete` | DELETE | `/examples/versions/{version_id}` | — | `ExampleVersionDeleteResult` |
| `getVersionExamplesVersionsVersionIdGet` | GET | `/examples/versions/{version_id}` | — | `ExampleVersionGet` |
| `getExampleExamplesExampleIdGet` | GET | `/examples/{example_id}` | — | `ExampleGet` |
| `listDependenciesExamplesExampleIdDependenciesGet` | GET | `/examples/{example_id}/dependencies` | — | `ExampleDependencyGet[]` |
| `addDependencyExamplesExampleIdDependenciesPost` | POST | `/examples/{example_id}/dependencies` | `ExampleDependencyCreate` | `ExampleDependencyGet` |
| `removeDependencyExamplesExampleIdDependenciesDependencyIdDelete` | DELETE | `/examples/{example_id}/dependencies/{dependency_id}` | — | `void` |
| `downloadExampleLatestExamplesExampleIdDownloadGet` | GET | `/examples/{example_id}/download` | — | `ExampleDownloadResponse` |
| `listVersionsExamplesExampleIdVersionsGet` | GET | `/examples/{example_id}/versions` | — | `ExampleVersionList[]` |
| `createVersionExamplesExampleIdVersionsPost` | POST | `/examples/{example_id}/versions` | `ExampleVersionCreate` | `ExampleVersionGet` |

## ExtensionsClient
- Base path: `/extensions`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listExtensionsExtensionsGet` | GET | `/extensions` | — | `string[]` |
| `getExtensionMetadataExtensionsExtensionIdentityGet` | GET | `/extensions/{extension_identity}` | — | `ExtensionMetadata` |
| `downloadExtensionExtensionsExtensionIdentityDownloadGet` | GET | `/extensions/{extension_identity}/download` | — | `void` |
| `listExtensionVersionsExtensionsExtensionIdentityVersionsGet` | GET | `/extensions/{extension_identity}/versions` | — | `ExtensionVersionListResponse` |
| `publishExtensionVersionExtensionsExtensionIdentityVersionsPost` | POST | `/extensions/{extension_identity}/versions` | — | `ExtensionPublishResponse` |
| `updateExtensionVersionExtensionsExtensionIdentityVersionsVersionPatch` | PATCH | `/extensions/{extension_identity}/versions/{version}` | `ExtensionVersionYankRequest` | `ExtensionVersionDetail` |

## ExtensionsGettingStartedClient
- Base path: `/extensions-getting-started`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getGettingStartedUrlExtensionsGettingStartedGet` | GET | `/extensions-getting-started` | — | `string` |

## ExtensionsPublicClient
- Base path: `/extensions-public`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getPublicExtensionUrlExtensionsPublicGet` | GET | `/extensions-public` | — | `string` |

## GitServersClient
- Base path: `/git-servers`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listGitServersEndpointGitServersGet` | GET | `/git-servers` | — | `GitServerGet[]` |
| `createGitServerEndpointGitServersPost` | POST | `/git-servers` | `GitServerCreate` | `GitServerGet` |
| `deleteGitServerEndpointGitServersServerIdDelete` | DELETE | `/git-servers/{server_id}` | — | `void` |
| `getGitServerEndpointGitServersServerIdGet` | GET | `/git-servers/{server_id}` | — | `GitServerGet` |
| `updateGitServerEndpointGitServersServerIdPatch` | PATCH | `/git-servers/{server_id}` | `GitServerUpdate` | `GitServerGet` |

## GroupsClient
- Base path: `/groups`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listGroupsGroupsGet` | GET | `/groups` | — | `GroupList[]` |
| `createGroupsGroupsPost` | POST | `/groups` | `GroupCreate` | `GroupGet` |
| `deleteGroupsGroupsIdDelete` | DELETE | `/groups/{id}` | — | `void` |
| `getGroupsGroupsIdGet` | GET | `/groups/{id}` | — | `GroupGet` |
| `updateGroupsGroupsIdPatch` | PATCH | `/groups/{id}` | `GroupUpdate` | `GroupGet` |

## InstanceClient
- Base path: `/instance-info`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getInstanceInfoInstanceInfoGet` | GET | `/instance-info` | — | `InstanceInfoGet` |

## InvitesClient
- Base path: `/invites`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getInvitePublicInvitesTokenGet` | GET | `/invites/{token}` | — | `InviteLinkPublic` |
| `acceptInviteInvitesTokenAcceptPost` | POST | `/invites/{token}/accept` | `InviteAccept` | `Record<string, unknown> & Record<string, unknown>` |

## LanguagesClient
- Base path: `/languages`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listLanguagesLanguagesGet` | GET | `/languages` | — | `LanguageList[]` |
| `getLanguagesLanguagesIdGet` | GET | `/languages/{id}` | — | `LanguageGet` |

## LecturersClient
- Base path: `/lecturers`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `lecturerListCourseContentsEndpointLecturersCourseContentsGet` | GET | `/lecturers/course-contents` | — | `CourseContentLecturerList[]` |
| `lecturerGetCourseContentsEndpointLecturersCourseContentsCourseContentIdGet` | GET | `/lecturers/course-contents/{course_content_id}` | — | `CourseContentLecturerGet` |
| `assignExampleToCourseContentLecturersCourseContentsCourseContentIdAssignExamplePost` | POST | `/lecturers/course-contents/{course_content_id}/assign-example` | `AssignExampleRequest` | `AssignExampleResponse` |
| `unassignExampleFromCourseContentLecturersCourseContentsCourseContentIdDeploymentDelete` | DELETE | `/lecturers/course-contents/{course_content_id}/deployment` | — | `UnassignExampleResponse` |
| `getCourseContentDeploymentLecturersCourseContentsCourseContentIdDeploymentGet` | GET | `/lecturers/course-contents/{course_content_id}/deployment` | — | `DeploymentGet` |
| `syncMemberGitlabPermissionsEndpointLecturersCourseMembersCourseMemberIdSyncGitlabPost` | POST | `/lecturers/course-members/{course_member_id}/sync-gitlab` | `GitLabSyncRequest` | `GitLabSyncResult` |
| `lecturerListCoursesEndpointLecturersCoursesGet` | GET | `/lecturers/courses` | — | `CourseList[]` |
| `lecturerGetCoursesEndpointLecturersCoursesCourseIdGet` | GET | `/lecturers/courses/{course_id}` | — | `CourseGet` |
| `getCourseDeploymentsEndpointLecturersCoursesCourseIdDeploymentsGet` | GET | `/lecturers/courses/{course_id}/deployments` | — | `CourseDeploymentGet` |
| `batchUpgradeVersionsEndpointLecturersCoursesCourseIdUpgradeVersionsPost` | POST | `/lecturers/courses/{course_id}/upgrade-versions` | `VersionUpgradeCreate` | `VersionUpgradeGet` |
| `validateCourseContentBatchLecturersCoursesCourseIdValidatePost` | POST | `/lecturers/courses/{course_id}/validate` | `ContentValidationCreate` | `ContentValidationGet` |

## MessagesClient
- Base path: `/messages`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listMessagesMessagesGet` | GET | `/messages` | — | `MessageList[]` |
| `createMessageMessagesPost` | POST | `/messages` | `MessageCreate` | `MessageGet` |
| `listMentionableUsersEndpointMessagesMentionableUsersGet` | GET | `/messages/mentionable-users` | — | `MessageMentionRef[]` |
| `deleteMessageMessagesIdDelete` | DELETE | `/messages/{id}` | — | `void` |
| `getMessageMessagesIdGet` | GET | `/messages/{id}` | — | `MessageGet` |
| `updateMessageMessagesIdPatch` | PATCH | `/messages/{id}` | `MessageUpdate` | `MessageGet` |
| `getMessageAuditMessagesIdAuditGet` | GET | `/messages/{id}/audit` | — | `void` |
| `markMessageUnreadMessagesIdReadsDelete` | DELETE | `/messages/{id}/reads` | — | `void` |
| `markMessageReadMessagesIdReadsPost` | POST | `/messages/{id}/reads` | — | `void` |
| `getMessageThreadEndpointMessagesIdThreadGet` | GET | `/messages/{id}/thread` | — | `MessageThread` |

## MiscClient
- Base path: `/`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getStatusHeadHead` | HEAD | `/` | — | `void` |

## OrganizationMembersClient
- Base path: `/organization-members`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listOrganizationMembersOrganizationMembersGet` | GET | `/organization-members` | — | `OrganizationMemberList[]` |
| `createOrganizationMembersOrganizationMembersPost` | POST | `/organization-members` | `OrganizationMemberCreate` | `OrganizationMemberGet` |
| `deleteOrganizationMembersOrganizationMembersIdDelete` | DELETE | `/organization-members/{id}` | — | `void` |
| `getOrganizationMembersOrganizationMembersIdGet` | GET | `/organization-members/{id}` | — | `OrganizationMemberGet` |
| `updateOrganizationMembersOrganizationMembersIdPatch` | PATCH | `/organization-members/{id}` | `OrganizationMemberUpdate` | `OrganizationMemberGet` |

## OrganizationRolesClient
- Base path: `/organization-roles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listOrganizationRolesOrganizationRolesGet` | GET | `/organization-roles` | — | `OrganizationRoleList[]` |
| `getOrganizationRolesOrganizationRolesIdGet` | GET | `/organization-roles/{id}` | — | `OrganizationRoleGet` |

## OrganizationsClient
- Base path: `/organizations`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listOrganizationsOrganizationsGet` | GET | `/organizations` | — | `OrganizationList[]` |
| `createOrganizationsOrganizationsPost` | POST | `/organizations` | `OrganizationCreate` | `OrganizationGet` |
| `deleteOrganizationsOrganizationsIdDelete` | DELETE | `/organizations/{id}` | — | `void` |
| `getOrganizationsOrganizationsIdGet` | GET | `/organizations/{id}` | — | `OrganizationGet` |
| `updateOrganizationsOrganizationsIdPatch` | PATCH | `/organizations/{id}` | `OrganizationUpdate` | `OrganizationGet` |
| `routeOrganizationsOrganizationsIdArchivePatch` | PATCH | `/organizations/{id}/archive` | — | `void` |
| `unarchiveOrganizationsOrganizationsIdUnarchivePatch` | PATCH | `/organizations/{id}/unarchive` | — | `void` |
| `deleteOrganizationEndpointOrganizationsOrganizationIdDelete` | DELETE | `/organizations/{organization_id}` | — | `CascadeDeleteResult` |
| `patchOrganizationsTokenOrganizationsOrganizationIdTokenPatch` | PATCH | `/organizations/{organization_id}/token` | `OrganizationUpdateTokenUpdate` | `void` |

## ProfilesClient
- Base path: `/profiles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listProfilesEndpointProfilesGet` | GET | `/profiles` | — | `ProfileList[]` |
| `createProfileEndpointProfilesPost` | POST | `/profiles` | `ProfileCreate` | `ProfileGet` |
| `deleteProfileEndpointProfilesIdDelete` | DELETE | `/profiles/{id}` | — | `void` |
| `getProfileEndpointProfilesIdGet` | GET | `/profiles/{id}` | — | `ProfileGet` |
| `updateProfileEndpointProfilesIdPatch` | PATCH | `/profiles/{id}` | `ProfileUpdate` | `ProfileGet` |

## ResultsClient
- Base path: `/results`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listResultsResultsGet` | GET | `/results` | — | `ResultList[]` |
| `createResultResultsPost` | POST | `/results` | `ResultCreate` | `ResultGet` |
| `deleteResultResultsResultIdDelete` | DELETE | `/results/{result_id}` | — | `void` |
| `getResultResultsResultIdGet` | GET | `/results/{result_id}` | — | `ResultGet` |
| `updateResultResultsResultIdPatch` | PATCH | `/results/{result_id}` | `ResultUpdate` | `ResultGet` |
| `listResultArtifactsEndpointResultsResultIdArtifactsGet` | GET | `/results/{result_id}/artifacts` | — | `ResultArtifactListItem[]` |
| `downloadResultArtifactsResultsResultIdArtifactsDownloadGet` | GET | `/results/{result_id}/artifacts/download` | — | `void` |
| `uploadResultArtifactsResultsResultIdArtifactsUploadPost` | POST | `/results/{result_id}/artifacts/upload` | — | `void` |
| `resultStatusResultsResultIdStatusGet` | GET | `/results/{result_id}/status` | — | `TaskStatus` |

## RolesClient
- Base path: `/roles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listRolesRolesGet` | GET | `/roles` | — | `RoleList[]` |
| `getRolesRolesIdGet` | GET | `/roles/{id}` | — | `RoleGet` |

## ServiceTypesClient
- Base path: `/service-types`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listServiceTypesServiceTypesGet` | GET | `/service-types` | — | `ServiceTypeList[]` |
| `createServiceTypeServiceTypesPost` | POST | `/service-types` | `ServiceTypeCreate` | `ServiceTypeGet` |
| `getServiceTypeServiceTypesEntityIdGet` | GET | `/service-types/{entity_id}` | — | `ServiceTypeGet` |
| `updateServiceTypeServiceTypesEntityIdPatch` | PATCH | `/service-types/{entity_id}` | `ServiceTypeUpdate` | `ServiceTypeGet` |

## ServicesClient
- Base path: `/service-accounts`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listServicesEndpointServiceAccountsGet` | GET | `/service-accounts` | — | `ServiceGet[]` |
| `createServiceEndpointServiceAccountsPost` | POST | `/service-accounts` | `ServiceCreate` | `ServiceGet` |
| `getServiceMeServiceAccountsMeGet` | GET | `/service-accounts/me` | — | `ServiceGet` |
| `deleteServiceEndpointServiceAccountsServiceIdDelete` | DELETE | `/service-accounts/{service_id}` | — | `void` |
| `getServiceEndpointServiceAccountsServiceIdGet` | GET | `/service-accounts/{service_id}` | — | `ServiceGet` |
| `updateServiceEndpointServiceAccountsServiceIdPatch` | PATCH | `/service-accounts/{service_id}` | `ServiceUpdate` | `ServiceGet` |
| `serviceHeartbeatEndpointServiceAccountsServiceIdHeartbeatPut` | PUT | `/service-accounts/{service_id}/heartbeat` | — | `void` |

## SessionsClient
- Base path: `/sessions`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listSessionsSessionsGet` | GET | `/sessions` | — | `SessionList[]` |
| `createSessionsSessionsPost` | POST | `/sessions` | `SessionCreate` | `SessionGet` |
| `getSessionStatsSessionsAdminStatsGet` | GET | `/sessions/admin/stats` | — | `void` |
| `listUserSessionsAdminSessionsAdminUsersUserIdGet` | GET | `/sessions/admin/users/{user_id}` | — | `SessionGet[]` |
| `revokeAllUserSessionsAdminSessionsAdminUsersUserIdAllDelete` | DELETE | `/sessions/admin/users/{user_id}/all` | — | `void` |
| `revokeSessionAdminSessionsAdminSessionIdDelete` | DELETE | `/sessions/admin/{session_id}` | — | `void` |
| `listMySessionsSessionsMeGet` | GET | `/sessions/me` | — | `SessionList[]` |
| `revokeAllMySessionsSessionsMeAllDelete` | DELETE | `/sessions/me/all` | — | `void` |
| `getCurrentSessionSessionsMeCurrentGet` | GET | `/sessions/me/current` | — | `SessionGet` |
| `revokeMySessionSessionsMeSessionIdDelete` | DELETE | `/sessions/me/{session_id}` | — | `void` |
| `deleteSessionsSessionsIdDelete` | DELETE | `/sessions/{id}` | — | `void` |
| `getSessionsSessionsIdGet` | GET | `/sessions/{id}` | — | `SessionGet` |
| `updateSessionsSessionsIdPatch` | PATCH | `/sessions/{id}` | `SessionUpdate` | `SessionGet` |

## StorageClient
- Base path: `/storage`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listBucketsStorageBucketsGet` | GET | `/storage/buckets` | — | `BucketInfo[]` |
| `createBucketStorageBucketsPost` | POST | `/storage/buckets` | `BucketCreate` | `BucketInfo` |
| `deleteBucketStorageBucketsBucketNameDelete` | DELETE | `/storage/buckets/{bucket_name}` | — | `void` |
| `getBucketStatsStorageBucketsBucketNameStatsGet` | GET | `/storage/buckets/{bucket_name}/stats` | — | `StorageUsageStats` |
| `copyObjectStorageCopyPost` | POST | `/storage/copy` | — | `void` |
| `downloadFileStorageDownloadObjectKeyGet` | GET | `/storage/download/{object_key}` | — | `void` |
| `listObjectsStorageObjectsGet` | GET | `/storage/objects` | — | `StorageObjectList[]` |
| `deleteObjectStorageObjectsObjectKeyDelete` | DELETE | `/storage/objects/{object_key}` | — | `void` |
| `getObjectInfoStorageObjectsObjectKeyGet` | GET | `/storage/objects/{object_key}` | — | `StorageObjectGet` |
| `generatePresignedUrlStoragePresignedUrlPost` | POST | `/storage/presigned-url` | `PresignedUrlRequest` | `PresignedUrlResponse` |
| `uploadFileStorageUploadPost` | POST | `/storage/upload` | — | `StorageObjectGet` |

## StudentProfilesClient
- Base path: `/student-profiles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listStudentProfilesStudentProfilesGet` | GET | `/student-profiles` | — | `StudentProfileList[]` |
| `createStudentProfileStudentProfilesPost` | POST | `/student-profiles` | `StudentProfileCreate` | `StudentProfileGet` |
| `deleteStudentProfileStudentProfilesIdDelete` | DELETE | `/student-profiles/{id}` | — | `void` |
| `getStudentProfileStudentProfilesIdGet` | GET | `/student-profiles/{id}` | — | `StudentProfileGet` |
| `updateStudentProfileStudentProfilesIdPatch` | PATCH | `/student-profiles/{id}` | `StudentProfileUpdate` | `StudentProfileGet` |

## StudentsClient
- Base path: `/students`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `studentListCourseContentsEndpointStudentsCourseContentsGet` | GET | `/students/course-contents` | — | `CourseContentStudentList[]` |
| `studentGetCourseContentEndpointStudentsCourseContentsCourseContentIdGet` | GET | `/students/course-contents/{course_content_id}` | — | `CourseContentStudentGet` |
| `studentListCoursesEndpointStudentsCoursesGet` | GET | `/students/courses` | — | `CourseStudentList[]` |
| `studentGetCourseEndpointStudentsCoursesCourseIdGet` | GET | `/students/courses/{course_id}` | — | `CourseStudentGet` |

## SubmissionGroupMembersClient
- Base path: `/submission-group-members`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listSubmissionGroupMembersSubmissionGroupMembersGet` | GET | `/submission-group-members` | — | `SubmissionGroupMemberList[]` |
| `createSubmissionGroupMembersSubmissionGroupMembersPost` | POST | `/submission-group-members` | `SubmissionGroupMemberCreate` | `SubmissionGroupMemberGet` |
| `deleteSubmissionGroupMembersSubmissionGroupMembersIdDelete` | DELETE | `/submission-group-members/{id}` | — | `void` |
| `getSubmissionGroupMembersSubmissionGroupMembersIdGet` | GET | `/submission-group-members/{id}` | — | `SubmissionGroupMemberGet` |
| `updateSubmissionGroupMembersSubmissionGroupMembersIdPatch` | PATCH | `/submission-group-members/{id}` | `SubmissionGroupMemberUpdate` | `SubmissionGroupMemberGet` |

## SubmissionGroupsClient
- Base path: `/submission-groups`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listSubmissionGroupsSubmissionGroupsGet` | GET | `/submission-groups` | — | `SubmissionGroupList[]` |
| `createSubmissionGroupsSubmissionGroupsPost` | POST | `/submission-groups` | `SubmissionGroupCreate` | `SubmissionGroupGet` |
| `deleteSubmissionGroupsSubmissionGroupsIdDelete` | DELETE | `/submission-groups/{id}` | — | `void` |
| `getSubmissionGroupsSubmissionGroupsIdGet` | GET | `/submission-groups/{id}` | — | `SubmissionGroupGet` |
| `updateSubmissionGroupsSubmissionGroupsIdPatch` | PATCH | `/submission-groups/{id}` | `SubmissionGroupUpdate` | `SubmissionGroupGet` |

## SubmissionsClient
- Base path: `/submissions`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listSubmissionArtifactsSubmissionsArtifactsGet` | GET | `/submissions/artifacts` | — | `SubmissionArtifactList[]` |
| `uploadSubmissionSubmissionsArtifactsPost` | POST | `/submissions/artifacts` | — | `SubmissionUploadResponseModel` |
| `downloadLatestSubmissionSubmissionsArtifactsDownloadGet` | GET | `/submissions/artifacts/download` | — | `void` |
| `getSubmissionArtifactSubmissionsArtifactsArtifactIdGet` | GET | `/submissions/artifacts/{artifact_id}` | — | `SubmissionArtifactGet` |
| `updateSubmissionArtifactSubmissionsArtifactsArtifactIdPatch` | PATCH | `/submissions/artifacts/{artifact_id}` | `SubmissionArtifactUpdate` | `SubmissionArtifactGet` |
| `downloadSubmissionArtifactSubmissionsArtifactsArtifactIdDownloadGet` | GET | `/submissions/artifacts/{artifact_id}/download` | — | `void` |
| `listArtifactGradesSubmissionsArtifactsArtifactIdGradesGet` | GET | `/submissions/artifacts/{artifact_id}/grades` | — | `SubmissionGradeList[]` |
| `createArtifactGradeEndpointSubmissionsArtifactsArtifactIdGradesPost` | POST | `/submissions/artifacts/{artifact_id}/grades` | `SubmissionGradeCreate` | `SubmissionGradeDetail` |
| `listArtifactReviewsSubmissionsArtifactsArtifactIdReviewsGet` | GET | `/submissions/artifacts/{artifact_id}/reviews` | — | `SubmissionReviewListItem[]` |
| `createArtifactReviewEndpointSubmissionsArtifactsArtifactIdReviewsPost` | POST | `/submissions/artifacts/{artifact_id}/reviews` | `SubmissionReviewCreate` | `SubmissionReviewListItem` |
| `createTestResultEndpointSubmissionsArtifactsArtifactIdTestPost` | POST | `/submissions/artifacts/{artifact_id}/test` | `ResultCreate` | `ResultList` |
| `listArtifactTestResultsSubmissionsArtifactsArtifactIdTestsGet` | GET | `/submissions/artifacts/{artifact_id}/tests` | — | `ResultGet[]` |
| `listGradesSubmissionsGradesGet` | GET | `/submissions/grades` | — | `SubmissionGradeList[]` |
| `deleteArtifactGradeSubmissionsGradesGradeIdDelete` | DELETE | `/submissions/grades/{grade_id}` | — | `void` |
| `updateArtifactGradeSubmissionsGradesGradeIdPatch` | PATCH | `/submissions/grades/{grade_id}` | `SubmissionGradeUpdate` | `SubmissionGradeDetail` |
| `deleteArtifactReviewSubmissionsReviewsReviewIdDelete` | DELETE | `/submissions/reviews/{review_id}` | — | `void` |
| `updateArtifactReviewSubmissionsReviewsReviewIdPatch` | PATCH | `/submissions/reviews/{review_id}` | `SubmissionReviewUpdate` | `SubmissionReviewListItem` |
| `updateTestResultEndpointSubmissionsTestsTestIdPatch` | PATCH | `/submissions/tests/{test_id}` | `ResultUpdate` | `ResultList` |

## SystemClient
- Base path: `/system`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `generateAssignmentsSystemCoursesCourseIdGenerateAssignmentsPost` | POST | `/system/courses/{course_id}/generate-assignments` | `GenerateAssignmentsRequest` | `GenerateAssignmentsResponse` |
| `generateStudentTemplateSystemCoursesCourseIdGenerateStudentTemplatePost` | POST | `/system/courses/{course_id}/generate-student-template` | `GenerateTemplateRequest` | `GenerateTemplateResponse` |
| `getCourseGitlabStatusSystemCoursesCourseIdGitlabStatusGet` | GET | `/system/courses/{course_id}/gitlab-status` | — | `Record<string, unknown> & Record<string, unknown>` |
| `createCourseAsyncSystemDeployCoursesPost` | POST | `/system/deploy/courses` | `CourseTaskRequest` | `TaskResponse` |
| `createHierarchySystemHierarchyCreatePost` | POST | `/system/hierarchy/create` | `Record<string, unknown> & Record<string, unknown>` | `Record<string, unknown> & Record<string, unknown>` |
| `getHierarchyStatusSystemHierarchyStatusWorkflowIdGet` | GET | `/system/hierarchy/status/{workflow_id}` | — | `Record<string, unknown> & Record<string, unknown>` |
| `activateMaintenanceSystemMaintenanceActivatePost` | POST | `/system/maintenance/activate` | `MaintenanceActivate` | `void` |
| `deactivateMaintenanceSystemMaintenanceDeactivatePost` | POST | `/system/maintenance/deactivate` | — | `void` |
| `cancelScheduledMaintenanceSystemMaintenanceScheduleDelete` | DELETE | `/system/maintenance/schedule` | — | `void` |
| `scheduleMaintenanceSystemMaintenanceSchedulePost` | POST | `/system/maintenance/schedule` | `MaintenanceSchedule` | `void` |
| `getMaintenanceStatusSystemMaintenanceStatusGet` | GET | `/system/maintenance/status` | — | `MaintenanceStatusGet` |

## TasksClient
- Base path: `/tasks`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listTasksTasksGet` | GET | `/tasks` | — | `Record<string, unknown> & Record<string, unknown>` |
| `submitTaskTasksSubmitPost` | POST | `/tasks/submit` | `TaskSubmission` | `Record<string, unknown> & Record<string, string>` |
| `listTaskTypesTasksTypesGet` | GET | `/tasks/types` | — | `string[]` |
| `getWorkerStatusTasksWorkersStatusGet` | GET | `/tasks/workers/status` | — | `Record<string, unknown> & Record<string, unknown>` |
| `deleteTaskTasksTaskIdDelete` | DELETE | `/tasks/{task_id}` | — | `void` |
| `getTaskTasksTaskIdGet` | GET | `/tasks/{task_id}` | — | `TaskInfo` |
| `cancelTaskTasksTaskIdCancelDelete` | DELETE | `/tasks/{task_id}/cancel` | — | `void` |
| `getTaskResultTasksTaskIdResultGet` | GET | `/tasks/{task_id}/result` | — | `TaskResult` |
| `getTaskStatusTasksTaskIdStatusGet` | GET | `/tasks/{task_id}/status` | — | `TaskInfo` |

## TestsClient
- Base path: `/tests`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `createTestRunTestsPost` | POST | `/tests` | `TestCreate` | `ResultList` |
| `getTestStatusTestsStatusResultIdGet` | GET | `/tests/status/{result_id}` | — | `void` |

## TokensClient
- Base path: `/api-tokens`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listTokensEndpointApiTokensGet` | GET | `/api-tokens` | — | `ApiTokenGet[]` |
| `createTokenEndpointApiTokensPost` | POST | `/api-tokens` | `ApiTokenCreate` | `ApiTokenCreateResponse` |
| `createTokenAdminEndpointApiTokensAdminCreatePost` | POST | `/api-tokens/admin/create` | `ApiTokenAdminCreate` | `ApiTokenCreateResponse` |
| `updateTokenAdminEndpointApiTokensAdminTokenIdPatch` | PATCH | `/api-tokens/admin/{token_id}` | `ApiTokenUpdate` | `ApiTokenGet` |
| `revokeTokenEndpointApiTokensTokenIdDelete` | DELETE | `/api-tokens/{token_id}` | — | `void` |
| `getTokenEndpointApiTokensTokenIdGet` | GET | `/api-tokens/{token_id}` | — | `ApiTokenGet` |

## TutorsClient
- Base path: `/tutors`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `downloadCourseContentDescriptionTutorsCourseContentsCourseContentIdDescriptionGet` | GET | `/tutors/course-contents/{course_content_id}/description` | — | `void` |
| `downloadCourseContentReferenceTutorsCourseContentsCourseContentIdReferenceGet` | GET | `/tutors/course-contents/{course_content_id}/reference` | — | `void` |
| `createTutorTestTutorsCourseContentsCourseContentIdTestPost` | POST | `/tutors/course-contents/{course_content_id}/test` | — | `TutorTestCreateResponse` |
| `tutorListCourseMembersEndpointTutorsCourseMembersGet` | GET | `/tutors/course-members` | — | `TutorCourseMemberList[]` |
| `tutorGetCourseMembersEndpointTutorsCourseMembersCourseMemberIdGet` | GET | `/tutors/course-members/{course_member_id}` | — | `TutorCourseMemberGet` |
| `tutorListCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsGet` | GET | `/tutors/course-members/{course_member_id}/course-contents` | — | `CourseContentStudentList[]` |
| `tutorGetCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdGet` | GET | `/tutors/course-members/{course_member_id}/course-contents/{course_content_id}` | — | `CourseContentStudentGet` |
| `tutorUpdateCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdPatch` | PATCH | `/tutors/course-members/{course_member_id}/course-contents/{course_content_id}` | `TutorGradeCreate` | `TutorGradeResponse` |
| `tutorListCoursesEndpointTutorsCoursesGet` | GET | `/tutors/courses` | — | `CourseTutorList[]` |
| `tutorGetCoursesEndpointTutorsCoursesCourseIdGet` | GET | `/tutors/courses/{course_id}` | — | `CourseTutorGet` |
| `tutorListSubmissionGroupsEndpointTutorsSubmissionGroupsGet` | GET | `/tutors/submission-groups` | — | `TutorSubmissionGroupList[]` |
| `tutorGetSubmissionGroupEndpointTutorsSubmissionGroupsSubmissionGroupIdGet` | GET | `/tutors/submission-groups/{submission_group_id}` | — | `TutorSubmissionGroupGet` |
| `getTutorTestEndpointTutorsTestsTestIdGet` | GET | `/tutors/tests/{test_id}` | — | `TutorTestGet` |
| `listTutorTestArtifactsEndpointTutorsTestsTestIdArtifactsGet` | GET | `/tutors/tests/{test_id}/artifacts` | — | `TutorTestArtifactList` |
| `downloadTutorTestArtifactsTutorsTestsTestIdArtifactsDownloadGet` | GET | `/tutors/tests/{test_id}/artifacts/download` | — | `void` |
| `uploadTutorTestArtifactsTutorsTestsTestIdArtifactsUploadPost` | POST | `/tutors/tests/{test_id}/artifacts/upload` | — | `void` |
| `downloadTutorTestInputTutorsTestsTestIdInputDownloadGet` | GET | `/tutors/tests/{test_id}/input/download` | — | `void` |
| `submitTutorTestResultsTutorsTestsTestIdResultsPost` | POST | `/tutors/tests/{test_id}/results` | `Record<string, unknown> & Record<string, unknown>` | `void` |
| `getTutorTestStatusEndpointTutorsTestsTestIdStatusGet` | GET | `/tutors/tests/{test_id}/status` | — | `TutorTestStatus` |

## UserClient
- Base path: `/user`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `getCurrentUserEndpointUserGet` | GET | `/user` | — | `UserGet` |
| `getCourseGitDescriptorEndpointUserCoursesCourseIdGitGet` | GET | `/user/courses/{course_id}/git` | — | `CourseGitDescriptor` |
| `provisionStudentRepositoryEndpointUserCoursesCourseIdProvisionRepositoryPost` | POST | `/user/courses/{course_id}/provision-repository` | — | `StudentRepositoryProvisioned` |
| `registerCurrentUserCourseAccountUserCoursesCourseIdRegisterPost` | POST | `/user/courses/{course_id}/register` | `CourseMemberProviderAccountUpdate` | `CourseMemberReadinessStatus` |
| `registerGitlabManagedEndpointUserCoursesCourseIdRegisterGitlabPost` | POST | `/user/courses/{course_id}/register-gitlab` | `CourseMemberValidationRequest` | `CourseMemberRepositoryGet` |
| `registerStudentRepositoryEndpointUserCoursesCourseIdRegisterRepositoryPost` | POST | `/user/courses/{course_id}/register-repository` | `CourseMemberRepositoryRegister` | `CourseMemberRepositoryGet` |
| `getStudentRepositoryEndpointUserCoursesCourseIdRepositoryGet` | GET | `/user/courses/{course_id}/repository` | — | `CourseMemberRepositoryGet | null` |
| `downloadTemplateArchiveEndpointUserCoursesCourseIdTemplateArchiveGet` | GET | `/user/courses/{course_id}/template/archive` | — | `void` |
| `validateCurrentUserCourseUserCoursesCourseIdValidatePost` | POST | `/user/courses/{course_id}/validate` | `CourseMemberValidationRequest` | `CourseMemberReadinessStatus` |
| `getCurrentUserScopesUserScopesGet` | GET | `/user/scopes` | — | `UserScopes` |
| `getCourseViewsForCurrentUserUserViewsGet` | GET | `/user/views` | — | `string[]` |
| `getCourseViewsForCurrentUserByCourseUserViewsCourseIdGet` | GET | `/user/views/{course_id}` | — | `string[]` |

## UserClient
- Base path: `/user-roles`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listUserRolesUserRolesGet` | GET | `/user-roles` | — | `UserRoleList[]` |
| `createUserRoleUserRolesPost` | POST | `/user-roles` | `UserRoleCreate` | `UserRoleGet` |
| `deleteUserRoleEndpointUserRolesUsersUserIdRolesRoleIdDelete` | DELETE | `/user-roles/users/{user_id}/roles/{role_id}` | — | `Record<string, unknown> & Record<string, unknown>` |
| `getUserRoleEndpointUserRolesUsersUserIdRolesRoleIdGet` | GET | `/user-roles/users/{user_id}/roles/{role_id}` | — | `UserRoleGet` |

## UsersClient
- Base path: `/users`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `listUsersUsersGet` | GET | `/users` | — | `UserList[]` |
| `createUsersUsersPost` | POST | `/users` | `UserCreate` | `UserGet` |
| `deleteUsersUsersIdDelete` | DELETE | `/users/{id}` | — | `void` |
| `getUsersUsersIdGet` | GET | `/users/{id}` | — | `UserGet` |
| `updateUsersUsersIdPatch` | PATCH | `/users/{id}` | `UserUpdate` | `UserGet` |
| `routeUsersUsersIdArchivePatch` | PATCH | `/users/{id}/archive` | — | `void` |
| `unarchiveUsersUsersIdUnarchivePatch` | PATCH | `/users/{id}/unarchive` | — | `void` |
| `banUserUsersUserIdBanPatch` | PATCH | `/users/{user_id}/ban` | `UserBanRequest | null` (optional) | `UserGet` |
| `unbanUserUsersUserIdUnbanPatch` | PATCH | `/users/{user_id}/unban` | — | `UserGet` |

## WorkspacesClient
- Base path: `/workspaces`
- Note: custom operations discovered from OpenAPI schema

| TS Method | HTTP | Path | Request | Response |
| --- | --- | --- | --- | --- |
| `assignRoleWorkspacesRolesAssignPost` | POST | `/workspaces/roles/assign` | `WorkspaceRoleAssign` | `WorkspaceRoleUser` |
| `listUsersWorkspacesRolesUsersGet` | GET | `/workspaces/roles/users` | — | `WorkspaceRoleUser[]` |
| `removeRoleWorkspacesRolesUsersUserIdRoleIdDelete` | DELETE | `/workspaces/roles/users/{user_id}/{role_id}` | — | `void` |
