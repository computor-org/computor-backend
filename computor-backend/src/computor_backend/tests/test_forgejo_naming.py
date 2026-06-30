"""Unit tests for per-course Forgejo org/repo naming (``utils.forgejo_naming``).

Covers the three guarantees: (1) names are always <=40 chars, (2) two distinct
courses never collide — including the "same course slug in two families" case,
and (3) the readable->family->suffix->hash ladder.
"""
import uuid

from computor_backend.utils.forgejo_naming import (
    ORG_NAME_MAX,
    allocate_course_org_name,
    course_org_candidates,
    student_repo_name_in_org,
)


def _free_set(taken):
    taken = set(taken)
    return lambda name: name not in taken


class TestCandidates:
    def test_short_then_family(self):
        cands = course_org_candidates("itpcp", "matlab", "2027", "id-1")
        assert cands[0] == "itpcp-2027"
        assert cands[1] == "itpcp-matlab-2027"

    def test_course_leaf_used_for_nested_path(self):
        # A nested course path keeps only its own leaf label.
        cands = course_org_candidates("itpcp", "matlab", "matlab.2027", "id-1")
        assert cands[0] == "itpcp-2027"
        assert cands[1] == "itpcp-matlab-2027"

    def test_dedup_when_family_is_empty(self):
        # No family segment -> the family form equals the short form; deduped.
        cands = course_org_candidates("itpcp", "", "2027", "id-1")
        assert cands == ["itpcp-2027"]

    def test_repeated_slug_keeps_both_forms(self):
        # Family and course slug coincide but both forms are still distinct.
        cands = course_org_candidates("itpcp", "2027", "2027", "id-1")
        assert cands == ["itpcp-2027", "itpcp-2027-2027"]


class TestAllocation:
    def test_takes_short_when_free(self):
        name = allocate_course_org_name(
            "itpcp", "matlab", "2027", "id-1", _free_set(set())
        )
        assert name == "itpcp-2027"

    def test_same_slug_two_families_does_not_collide(self):
        # Family A grabs the short name; family B must fall to the family form.
        a = allocate_course_org_name("itpcp", "matlab", "2027", "id-a", _free_set(set()))
        b = allocate_course_org_name(
            "itpcp", "physics", "2027", "id-b", _free_set({a})
        )
        assert a == "itpcp-2027"
        assert b == "itpcp-physics-2027"
        assert a != b

    def test_numeric_suffix_last_resort(self):
        # Both readable forms taken -> numeric suffix on the family form.
        taken = {"itpcp-2027", "itpcp-physics-2027"}
        name = allocate_course_org_name(
            "itpcp", "physics", "2027", "id-b", _free_set(taken)
        )
        assert name == "itpcp-physics-2027-2"

    def test_suffix_increments_until_free(self):
        taken = {"itpcp-2027", "itpcp-physics-2027", "itpcp-physics-2027-2"}
        name = allocate_course_org_name(
            "itpcp", "physics", "2027", "id-b", _free_set(taken)
        )
        assert name == "itpcp-physics-2027-3"


class TestLengthCap:
    def test_long_inputs_are_capped_and_hashed(self):
        org = "really-long-organization-slug-that-is-huge"
        fam = "winter-semester-bachelor-informatics"
        course = "introduction-to-numerical-mathematics-2027"
        cid = str(uuid.uuid4())
        for name in course_org_candidates(org, fam, course, cid):
            assert len(name) <= ORG_NAME_MAX
            assert not name.startswith("-") and not name.endswith("-")

    def test_capped_names_stay_distinct_via_hash(self):
        org = "really-long-organization-slug-that-is-huge"
        fam = "winter-semester-bachelor-informatics"
        course = "introduction-to-numerical-mathematics-2027"
        # Beyond 40 chars the readable forms collapse to one hashed name, so the
        # course-id hash is what keeps two different courses apart.
        n1 = course_org_candidates(org, fam, course, "course-id-one")[0]
        n2 = course_org_candidates(org, fam, course, "course-id-two")[0]
        assert len(n1) <= ORG_NAME_MAX and len(n2) <= ORG_NAME_MAX
        assert n1 != n2

    def test_suffix_form_respects_cap(self):
        org = "really-long-organization-slug-that-is-huge"
        fam = "winter-semester-bachelor-informatics"
        course = "introduction-to-numerical-mathematics-2027"
        cid = str(uuid.uuid4())
        # Force the allocator down to a numeric suffix.
        readable = set(course_org_candidates(org, fam, course, cid))
        name = allocate_course_org_name(org, fam, course, cid, _free_set(readable))
        assert len(name) <= ORG_NAME_MAX
        assert name not in readable


class TestStudentRepoName:
    def test_plain_handle(self):
        assert student_repo_name_in_org("mmusterm") == "mmusterm"

    def test_handle_equal_to_staff_repo_is_suffixed(self):
        # A student whose handle is "reference"/"template" must not adopt a staff repo.
        assert student_repo_name_in_org("reference") == "reference-repo"
        assert student_repo_name_in_org("template") == "template-repo"

    def test_distinct_handles_distinct_repos(self):
        assert student_repo_name_in_org("alice") != student_repo_name_in_org("bob")
