# Suites

Numbered prefixes drive execution order. Later suites build on state
created by earlier ones (see the no-rollback policy in the top-level
README).

| Suite | Focus | Milestone |
|-------|-------|-----------|
| `01_smoke` | Services reachable, OpenAPI advertises paths | M2 |
| `02_auth` | Login, token refresh, bearer / API-token | M2 |
| `03_permissions` | RBAC matrix: endpoint × role → expected status | M3 |
| `04_deployment` | `deploy_computor_hierarchy` workflow, GitLab groups appear | M4 |
| `05_examples` | Upload Python examples, assign to course content (no tests yet) | M5 |
| `06_release` | `generate_student_template_v2`, student-template repo contents (no tests yet) | M5 |
| `07_student_workflow` | Student fork, submission upload, `student_testing` (no tests yet) | M6 |
| `08_full_lifecycle` | Golden-path end-to-end (no tests yet) | M7 |
