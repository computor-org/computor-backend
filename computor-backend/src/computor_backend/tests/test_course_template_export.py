"""Tests for the hierarchical course-template export helpers."""

import io
import zipfile

import pytest

from computor_backend.api.courses import (
    TEMPLATE_DOWNLOAD_LIMIT,
    check_template_download_rate_limit,
)
from computor_backend.business_logic.course_template_export import (
    _sanitize_segment,
    build_display_names,
    remap_archive_to_hierarchy,
)


def make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def zip_names(data: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {info.filename for info in zf.infolist() if not info.is_dir()}


class TestSanitizeSegment:
    def test_plain_title_kept(self):
        assert _sanitize_segment("Loops and Conditions", "loops") == "Loops and Conditions"

    def test_forbidden_chars_replaced_and_whitespace_collapsed(self):
        assert _sanitize_segment('a/b\\c:d*e?f"g<h>i|j', "x") == "a b c d e f g h i j"

    def test_trailing_dots_and_spaces_stripped(self):
        assert _sanitize_segment("  Title.. ", "x") == "Title"

    def test_empty_title_falls_back(self):
        assert _sanitize_segment(None, "unit_1") == "unit_1"
        assert _sanitize_segment("///", "unit_1") == "unit_1"


class TestBuildDisplayNames:
    def test_nested_tree_uses_titles(self):
        names = build_display_names(
            [
                ("unit_1", "Loops", 1.0),
                ("unit_1.fib", "Fibonacci", 1.0),
                ("unit_1.primes", "Prime Numbers", 2.0),
            ]
        )
        assert names == {
            "unit_1": "Loops",
            "unit_1.fib": "Fibonacci",
            "unit_1.primes": "Prime Numbers",
        }

    def test_missing_title_falls_back_to_path_leaf(self):
        names = build_display_names([("unit_1", None, 1.0), ("unit_1.fib", "", 1.0)])
        assert names == {"unit_1": "unit_1", "unit_1.fib": "fib"}

    def test_sibling_collision_suffixed_in_position_order(self):
        names = build_display_names(
            [
                ("b", "Intro", 2.0),
                ("a", "Intro", 1.0),
                ("c", "intro", 3.0),
            ]
        )
        assert names["a"] == "Intro"
        assert names["b"] == "Intro (2)"
        assert names["c"] == "intro (3)"

    def test_same_title_in_different_parents_no_suffix(self):
        names = build_display_names(
            [
                ("u1", "Unit", 1.0),
                ("u2", "Unit 2", 2.0),
                ("u1.a", "Warmup", 1.0),
                ("u2.a", "Warmup", 1.0),
            ]
        )
        assert names["u1.a"] == "Warmup"
        assert names["u2.a"] == "Warmup"


class TestRemapArchive:
    def test_relocates_mapped_dirs_and_drops_the_rest(self):
        src = make_zip(
            {
                "student-template/README.md": b"root readme",
                "student-template/loops.fib/README.md": b"fib",
                "student-template/loops.fib/main.py": b"print()",
                "student-template/loops.primes/README.md": b"primes",
                "student-template/stale_dir/file.txt": b"stale",
            }
        )
        result = remap_archive_to_hierarchy(
            src,
            {
                "loops.fib": ["Loops/Fibonacci"],
                "loops.primes": ["Loops/Prime Numbers"],
            },
        )
        assert zip_names(result) == {
            "Loops/Fibonacci/README.md",
            "Loops/Fibonacci/main.py",
            "Loops/Prime Numbers/README.md",
        }
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            assert zf.read("Loops/Fibonacci/main.py") == b"print()"

    def test_gitlab_style_wrapper_stripped(self):
        src = make_zip({"repo-main-abc123/ex1/a.txt": b"a"})
        result = remap_archive_to_hierarchy(src, {"ex1": ["Unit/One"]})
        assert zip_names(result) == {"Unit/One/a.txt"}

    def test_archive_without_wrapper_dir(self):
        src = make_zip({"ex1/a.txt": b"a", "README.md": b"r"})
        result = remap_archive_to_hierarchy(src, {"ex1": ["Unit/One"]})
        assert zip_names(result) == {"Unit/One/a.txt"}

    def test_repo_dir_prefix_of_another_matches_most_specific(self):
        src = make_zip(
            {
                "w/ex/a.txt": b"outer",
                "w/ex/sub/b.txt": b"inner",
            }
        )
        result = remap_archive_to_hierarchy(
            src, {"ex": ["Outer"], "ex/sub": ["Inner"]}
        )
        assert zip_names(result) == {"Outer/a.txt", "Inner/b.txt"}

    def test_multiple_targets_for_one_repo_dir(self):
        src = make_zip({"w/ex/a.txt": b"a"})
        result = remap_archive_to_hierarchy(src, {"ex": ["First", "Second"]})
        assert zip_names(result) == {"First/a.txt", "Second/a.txt"}

    def test_empty_mapping_yields_empty_zip(self):
        src = make_zip({"w/ex/a.txt": b"a"})
        assert zip_names(remap_archive_to_hierarchy(src, {})) == set()


class FakeCache:
    """Minimal async stand-in for the Redis client (incr/expire only)."""

    def __init__(self, raises: bool = False):
        self.counters: dict[str, int] = {}
        self.expires: dict[str, int] = {}
        self.raises = raises

    async def incr(self, key: str) -> int:
        if self.raises:
            raise ConnectionError("redis down")
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expires[key] = seconds


class TestDownloadRateLimit:
    @pytest.mark.asyncio
    async def test_allows_up_to_the_limit_then_blocks(self):
        cache = FakeCache()
        allowed = [
            not await check_template_download_rate_limit("u1", cache)
            for _ in range(TEMPLATE_DOWNLOAD_LIMIT + 2)
        ]
        assert allowed == [True] * TEMPLATE_DOWNLOAD_LIMIT + [False, False]

    @pytest.mark.asyncio
    async def test_window_set_once_so_blocked_requests_do_not_extend_it(self):
        cache = FakeCache()
        for _ in range(TEMPLATE_DOWNLOAD_LIMIT + 3):
            await check_template_download_rate_limit("u1", cache)
        assert list(cache.expires) == ["rate_limit:template_download:u1"]

    @pytest.mark.asyncio
    async def test_budget_is_per_user(self):
        cache = FakeCache()
        for _ in range(TEMPLATE_DOWNLOAD_LIMIT + 1):
            await check_template_download_rate_limit("u1", cache)
        assert await check_template_download_rate_limit("u2", cache) is False

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_is_unavailable(self):
        assert await check_template_download_rate_limit("u1", FakeCache(raises=True)) is False
