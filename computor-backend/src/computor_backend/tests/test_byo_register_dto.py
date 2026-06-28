"""Validator tests for the BYO repository registration DTO."""
import pytest

from computor_types.course_git import CourseMemberRepositoryRegister


def test_requires_at_least_one_location():
    with pytest.raises(ValueError):
        CourseMemberRepositoryRegister(mode="external")


def test_accepts_http_url():
    r = CourseMemberRepositoryRegister(http_url="https://gitlab.example/g/p.git")
    assert r.mode == "external" and r.http_url.endswith(".git")


def test_default_mode_is_external():
    assert CourseMemberRepositoryRegister(web_url="https://gitlab.example/g/p").mode == "external"


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        CourseMemberRepositoryRegister(mode="bitbucket", http_url="https://x")


def test_ssh_url_alone_is_enough():
    r = CourseMemberRepositoryRegister(ssh_url="git@gitlab.example:g/p.git")
    assert r.ssh_url
