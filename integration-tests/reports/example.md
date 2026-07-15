# Integration Test Report

> **Illustrative sample.** This documents the shape of the report `reporting.py`
> writes to `reports/latest.md` at the end of a green run — committed so the
> format is reviewable without standing up the stack. Regenerate the real report
> against the live stack with `make report`. Rows below are representative; a live
> run renders every suite, the full 25-endpoint permission matrix, and any
> failures/skips.

**Generated:** 2026-07-14 18:20:11 UTC · **Duration:** 121.47s
**Branch:** `feat/testing-strategy` · **Commit:** `df6a58a7` — test(integration): student workflow + grading — full lifecycle

## Summary

| Outcome | Count |
|---|---:|
| ✓ PASS | 248 |
| ⊘ SKIP | 4 |
| **Total** | **252** |

## Permission Matrix

Rows = endpoint, columns = role. Each cell is the observed HTTP status code. ✓ = matches expected, ✗ = mismatch. Missing cells are not asserted by the current matrix.

| Endpoint | admin | uma | orga | exma | lena | tobi | student | anon |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `GET /courses` | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 401 |
| `GET /examples` | ✓ 200 | ✓ 403 | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 403 | ✓ 403 | ✓ 401 |
| `GET /organizations/{organization_id}` | ✓ 200 | ✓ 404 | ✓ 200 | ✓ 404 | ✓ 200 | ✓ 200 | ✓ 200 | ✓ 401 |
| `GET /courses/{course_id}/git` | ✓ 200 | ✓ 403 | ✓ 200 | ✓ 403 | ✓ 200 | ✓ 403 | ✓ 403 | ✓ 401 |
| `PATCH /courses/{course_id}` | ✓ 200 | ✓ 404 | ✓ 200 | ✓ 404 | ✓ 200 | ✓ 404 | ✓ 404 | ✓ 401 |
| `POST /admin/invites` | ✓ 201 | ✓ 201 | ✓ 403 | ✓ 403 | ✓ 403 | ✓ 403 | ✓ 403 | ✓ 401 |

_(sample — a live run renders all 25 matrix endpoints × 8 roles.)_

## Golden-Path Grading Outcomes

Each cell is the test result (0.0–1.0) for that student's submission; the final column is the tutor's average grade. Correct ≈ 100%, empty ≈ 0%, mixed ≈ 50% — the whole lifecycle, end to end.

| Student | a01 | a02 | a03 | a04 | a05 | a06 | Avg grade |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `s_correct` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** |
| `s_empty` | 0.00 | 0.00 | 0.50 | 0.00 | 0.00 | 0.00 | **0.00** |
| `s_mixed` | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | **0.50** |

## suites/01_smoke

| Test | Result | Duration |
|---|---|---:|
| `test_api_reachable` | ✓ PASS | 0.04s |
| `test_keycloak_realm_reachable` | ✓ PASS | 0.12s |
| `test_forgejo_health` | ✓ PASS | 0.09s |

## suites/02_auth

| Test | Result | Duration |
|---|---|---:|
| `test_sso_login_returns_admin` | ✓ PASS | 0.31s |
| `test_absent_token_rejected` | ✓ PASS | 0.05s |
| `test_invite_accept_then_login` | ✓ PASS | 0.88s |

## suites/08_full_lifecycle

| Test | Result | Duration |
|---|---|---:|
| `test_every_cell_graded` | ✓ PASS | 1.42s |
| `test_overall_average_grading_matches` | ✓ PASS | 0.36s |
| `test_student_sees_own_grade` | ✓ PASS | 0.21s |

## Skipped

| Test | Reason |
|---|---|
| `suites/03_permissions/test_lena.py::test_lena[POST /git-servers]` | matrix cell not asserted for lena |
| `suites/03_permissions/test_orga.py::test_orga[POST /git-servers]` | matrix cell not asserted for orga |
| `suites/03_permissions/test_admin.py::test_admin[POST /git-servers]` | matrix cell not asserted for admin |
| `suites/03_permissions/test_uma.py::test_uma[POST /admin/invites]` | matrix cell not asserted for uma |
