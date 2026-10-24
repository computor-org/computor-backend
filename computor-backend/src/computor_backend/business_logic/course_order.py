"""Shared ordering for native course lists and catalogs."""

from computor_backend.model.course import Course


def course_ordering():
    return (Course.position.asc().nullslast(), Course.title.asc().nullslast(), Course.id.asc())
