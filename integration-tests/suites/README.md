# Suites

Numbered prefixes drive execution order. Later suites build on state
created by earlier ones (see the no-rollback policy in the top-level
README).

| Suite | Focus | Milestone |
|-------|-------|-----------|
| `01_smoke` | Services reachable, OpenAPI advertises paths | M2 |
| `02_auth` | SSO login, token refresh, API tokens, invite onboarding | M2 |
| `03_permissions` | RBAC matrix: endpoint × role → expected status | M3 |
| `04_contracts` | Payload validation + error contracts (planned; replaces the removed GitLab deployment suite) | M4 |
| `05_examples` | Upload Python examples, assign to course content | M5 |
| `06_release` | Course + Forgejo binding, `generate_student_template_v2`, template repo contents | M5 |
| `07_student_workflow` | Repo provisioning, submission upload, `student_testing` | M6 |
| `08_full_lifecycle` | Tutor grading, golden-path end-to-end | M7 |

See `testing-strategy/06-integration-suites.md` for the full per-suite spec.
