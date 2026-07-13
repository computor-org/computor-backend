# 05 — Payload & Exception Testing

Goal: assert not just *that* requests fail, but that they fail with the **documented
error contract** — and that valid payloads round-trip with the documented response
shape. Lives in a new suite `suites/04_contracts/` (the old `04_deployment` GitLab suite
is deleted; the number is reused).

## 1. The error contract

- Registry: `computor_backend/exceptions/error_registry.py` (definitions +
  `get_all_error_codes`); handlers in `exceptions/error_handlers.py` attach
  `error_code` to the JSON body when it matches the `PREFIX_NNN` shape.
- **Request-validation errors are `400` + `error_code: "VAL_001"`** — not FastAPI's
  default 422 (`error_handlers.py:75-95`). This repeatedly surprises; assert it once
  centrally and per representative DTO.
- Client-side mirror for typed assertions: `computor_types/generated/error_codes.py`
  (e.g. `AUTHZ_006` consent). Tests import from `computor_types` (the harness already
  puts the sibling package on `sys.path`).

Shared helper (new `helpers/assertions.py` — finally giving the empty `helpers/` its
promised purpose):

```python
def assert_error(resp, status: int, code: str | None = None):
    assert resp.status_code == status, resp.text
    if code is not None:
        assert resp.json().get("error_code") == code, resp.text

def assert_shape(resp, model):   # pydantic DTO from computor_types
    return model.model_validate(resp.json())
```

`assert_shape` gives every happy-path contract test a typed response check for free —
that is the "proper payloads" half of the requirement.

## 2. Validation-shape cases (VAL_001)

One test per representative DTO family (not per endpoint — the handler is global):

| Endpoint | Bad payload | Expect |
|---|---|---|
| `POST /admin/invites` | empty body; `max_uses: 0`; `max_uses: 101`; `expires_in_days: 366` | 400 `VAL_001` |
| `POST /invites/{token}/accept` | missing `password`; malformed email | 400 `VAL_001` |
| `POST /organizations` | invalid ltree `path` | 400 `VAL_001` |
| `POST /course-contents` | unknown `course_content_type_id`; bad ltree | 400/404 per handler |
| `POST /lecturers/course-contents/{id}/assign-example` | non-semver `version_tag` | 400 `VAL_001` |
| `PATCH /tutors/...` grade | `grade: 1.5`; `grade: -0.1`; unknown `status` | 400 `VAL_001` |

## 3. Domain-exception cases (business rules, distinct codes/statuses)

| Area | Case | Expect |
|---|---|---|
| Invites | expired token accept; revoked token accept; `use_count == max_uses` accept; email-restricted invite with wrong email; **double accept** of a `max_uses:1` token | 4xx with stable code/message (pin whatever the registry defines; add codes to the registry if missing — noted as a possible small backend follow-up) |
| Course members | `_student` member without `course_group_id` (`course_member_check`) | 4xx, asserted shape |
| Course git binding | rebind after materialization (`locked`) | 4xx + `lock_reason` surfaced |
| Hierarchy delete | delete org/family with children | **409** (bottom-up rule) |
| Examples | upload without `meta.yaml`; broken zip; re-upload same `version_tag` | 4xx |
| Submissions | exceed `max_submissions`; ZIP > 10 MB cap; unknown `submission_group_id` | 4xx |
| Tests | exceed `max_test_runs`; second `POST /tests` within 1s | **429 `RATE_003`** (rate case marked `slow`, run serially) |
| Auth | bogus bearer; revoked API token; malformed `ctp_` token (`validate_token_format`) | 401 |

## 4. Happy-path payload contracts

For each scenario endpoint ([03](03-personas-and-scenario.md)), one contract test
validates the response against its `computor_types` DTO via `assert_shape`:
invite create/get/public-get, org/family/course get, git binding get
(`has_token` never leaks the token; URLs are **public-host**, never
`forgejo:3030` — regression guard for the `to_public_git_url` boundary),
provision-repository response (one-time token present on POST, absent on GET),
submission upload response, result get, tutor grade response, gradings list.

## 5. Placement & style

- Suite `suites/04_contracts/`, marker `contracts`; files grouped per area
  (`test_invites_contract.py`, `test_submissions_contract.py`, …).
- Contract tests **reuse** scenario fixtures (personas, course) but never mutate golden-
  path state destructively — anything destructive builds its own namespaced object
  (`it.contracts.*`).
- Every case asserts `(status, error_code)`, not status alone, except where the registry
  genuinely defines no code (then assert the `detail` message shape and leave a comment
  referencing the registry gap).
