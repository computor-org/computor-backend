"""
Guard against delete cascades configured on the wrong side of a relationship.

A `delete` cascade on a MANY-TO-ONE relationship means "deleting the child also
deletes the parent it points at" - almost never what is intended, and silently
destructive because the DB-level ON DELETE CASCADE chains then fire from the
parent downwards.

Regression test for the `Result.course_content` cascade, which turned
`DELETE /results/{id}` into "delete the whole assignment".
"""

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import class_mapper

from computor_backend.model import Base, Result, CourseContent


def _all_mappers():
    """Every mapper registered on the declarative Base."""
    Base.registry.configure()
    return list(Base.registry.mappers)


@pytest.mark.unit
class TestRelationshipCascades:
    """No many-to-one relationship may carry a delete cascade."""

    def test_no_delete_cascade_on_many_to_one(self):
        offenders = []
        for mapper in _all_mappers():
            for rel in mapper.relationships:
                if rel.direction.name != "MANYTOONE":
                    continue
                if rel.cascade.delete or rel.cascade.delete_orphan:
                    offenders.append(
                        f"{mapper.class_.__name__}.{rel.key} "
                        f"(cascade={rel.cascade})"
                    )

        assert not offenders, (
            "delete cascade configured on the many-to-one side - deleting the child "
            "would delete its parent:\n  " + "\n  ".join(offenders)
        )

    def test_result_does_not_cascade_into_course_content(self):
        """The specific regression: one deleted Result must not take the assignment."""
        rel = class_mapper(Result).relationships["course_content"]
        assert rel.direction.name == "MANYTOONE"
        assert not rel.cascade.delete
        assert not rel.cascade.delete_orphan

    def test_course_content_still_owns_its_results(self):
        """The cascade belongs on the parent side and must stay there."""
        rel = class_mapper(CourseContent).relationships["results"]
        assert rel.direction.name == "ONETOMANY"
        assert rel.cascade.delete

    def test_result_course_content_relationship_is_still_usable(self):
        """Removing the cascade must not break the mapping itself."""
        assert sa_inspect(Result).relationships["course_content"].mapper.class_ is CourseContent
