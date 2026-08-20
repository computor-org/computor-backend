"""Guards the ``**list_data`` merge in ``view_mappers``.

The detailed student/tutor DTOs are built as "the List payload plus a few
extras": ``model_dump(exclude=...)`` is unpacked and the richer variants are
then passed explicitly. That shortcut has a sharp edge — the moment a field is
added to the *List* DTO while an explicit kwarg of the same name still stands
after the unpack, every call to the endpoint dies with

    TypeError: CourseContentStudentGet() got multiple values for
               keyword argument 'description'

which is a hard 500, not a validation error, so no amount of DTO tightening
catches it. That is exactly what happened when ``description`` was added to
``CourseContentStudentList``: the detail path had carried an explicit
``description=`` since long before, and the student course-content detail
endpoint 500'd for every student.

This test reads the source rather than calling the mapper: the collision is a
property of the call site, and reproducing it live would need the full course /
submission-group / grading fixture stack.
"""
import ast
import inspect

import pytest

from computor_backend.repositories import view_mappers


def _dump_merge_calls(module):
    """Yield (call_node, dumped_variable) for every ``Model(**var, ...)`` call.

    Only calls whose first argument is a ``**`` unpack of a local variable are
    interesting — that is the shape the mappers use.
    """
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        starstar = [k for k in node.keywords if k.arg is None]
        if len(starstar) != 1 or not isinstance(starstar[0].value, ast.Name):
            continue
        yield node, starstar[0].value.id


def _dumped_field_names(tree, variable):
    """Fields carried by ``variable = <Model>(...).model_dump(exclude={...})``.

    Returns the *declared* fields of the model the dump came from, minus the
    excluded names — i.e. exactly the keys that will land in the unpack.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if variable not in targets:
            continue
        call = node.value
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "model_dump"
            and isinstance(call.func.value, ast.Name)
        ):
            continue

        source_var = call.func.value.id
        excluded = set()
        for kw in call.keywords:
            if kw.arg == "exclude" and isinstance(kw.value, ast.Set):
                excluded = {
                    e.value for e in kw.value.elts if isinstance(e, ast.Constant)
                }

        model_name = _assigned_model_name(tree, source_var)
        model = getattr(view_mappers, model_name, None)
        if model is None or not hasattr(model, "model_fields"):
            return None
        return set(model.model_fields) - excluded
    return None


def _assigned_model_name(tree, variable):
    """Name of the model class in ``variable = SomeModel(...)``."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if variable not in [t.id for t in node.targets if isinstance(t, ast.Name)]:
            continue
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            return node.value.func.id
    return ""


def test_no_explicit_kwarg_collides_with_the_unpacked_dump():
    tree = ast.parse(inspect.getsource(view_mappers))
    checked = 0

    for call, dumped_var in _dump_merge_calls(view_mappers):
        carried = _dumped_field_names(tree, dumped_var)
        if carried is None:
            continue
        checked += 1

        explicit = {k.arg for k in call.keywords if k.arg is not None}
        collisions = explicit & carried
        assert not collisions, (
            f"{call.func.id}(**{dumped_var}, ...) passes {sorted(collisions)} "
            f"explicitly while the unpack already carries it — this raises "
            f"TypeError at runtime. Either drop the explicit kwarg or add the "
            f"field to the model_dump(exclude=...) set."
        )

    assert checked, "expected at least one **dump merge site in view_mappers"


def test_detail_dto_accepts_every_field_the_list_dto_carries():
    """The unpack is only safe while Get is a superset of List.

    ``CourseContentStudentGet`` does not inherit from ``CourseContentStudentList``,
    so a field added to the List DTO alone reaches the Get constructor as an
    unexpected keyword.
    """
    list_fields = set(view_mappers.CourseContentStudentList.model_fields)
    get_fields = set(view_mappers.CourseContentStudentGet.model_fields)
    # These are re-passed explicitly as their richer Get variants.
    excluded = {"course_content_type", "submission_group", "result"}

    missing = (list_fields - excluded) - get_fields
    assert not missing, (
        f"CourseContentStudentGet is missing {sorted(missing)}, which "
        f"CourseContentStudentList carries into it via **list_data"
    )


def test_description_survives_into_the_student_detail_dto():
    """The field whose duplication caused the 500 must still be on both DTOs."""
    assert "description" in view_mappers.CourseContentStudentList.model_fields
    assert "description" in view_mappers.CourseContentStudentGet.model_fields
