"""Regression test for permitted() role-floor independence.

Principal.permitted() used to memoize results under a key that ignored
``course_role``, so two checks on the same resource with different role
floors shared one cache slot — whichever ran first fixed the answer for
the other. These tests assert the checks stay independent in both orders.
"""

from computor_backend.permissions.principal import Claims, Principal


def _tutor_principal(course_id: str) -> Principal:
    return Principal(
        user_id="user-1",
        claims=Claims(dependent={"course": {course_id: {"_tutor"}}}),
    )


def test_role_floor_checks_are_independent_low_then_high():
    course_id = "11111111-1111-1111-1111-111111111111"
    principal = _tutor_principal(course_id)

    assert principal.permitted("course", "get", course_id, course_role="_tutor") is True
    assert principal.permitted("course", "get", course_id, course_role="_lecturer") is False


def test_role_floor_checks_are_independent_high_then_low():
    course_id = "11111111-1111-1111-1111-111111111111"
    principal = _tutor_principal(course_id)

    assert principal.permitted("course", "get", course_id, course_role="_lecturer") is False
    assert principal.permitted("course", "get", course_id, course_role="_tutor") is True
