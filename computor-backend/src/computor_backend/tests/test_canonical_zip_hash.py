"""Unit tests for ``_canonical_zip_hash`` — the content identifier for git-less
(download-mode) submissions.

It must be deterministic and independent of zip ordering/timestamps, so an
unchanged re-upload yields the same ``version_identifier`` (and the existing
dedup blocks it), while any content/path change yields a different one.
"""
import io
import zipfile

from computor_backend.business_logic.submissions import _canonical_zip_hash


def _zip(files, order=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name in (order or list(files)):
            z.writestr(name, files[name])
    return buf.getvalue()


class TestCanonicalZipHash:
    def test_same_content_same_hash(self):
        files = {"a.py": b"print(1)", "b.txt": b"hello"}
        assert _canonical_zip_hash(_zip(files)) == _canonical_zip_hash(_zip(files))

    def test_order_independent(self):
        files = {"a.py": b"print(1)", "b.txt": b"hello"}
        h1 = _canonical_zip_hash(_zip(files, order=["a.py", "b.txt"]))
        h2 = _canonical_zip_hash(_zip(files, order=["b.txt", "a.py"]))
        assert h1 == h2

    def test_changed_content_changes_hash(self):
        assert _canonical_zip_hash(_zip({"a.py": b"print(1)"})) != \
            _canonical_zip_hash(_zip({"a.py": b"print(2)"}))

    def test_changed_path_changes_hash(self):
        assert _canonical_zip_hash(_zip({"a.py": b"x"})) != \
            _canonical_zip_hash(_zip({"b.py": b"x"}))

    def test_prefix_and_length(self):
        h = _canonical_zip_hash(_zip({"a.py": b"x"}))
        assert h.startswith("content-")
        assert len(h) == len("content-") + 64  # sha256 hexdigest

    def test_non_zip_is_deterministic(self):
        assert _canonical_zip_hash(b"not a zip") == _canonical_zip_hash(b"not a zip")
        assert _canonical_zip_hash(b"not a zip").startswith("content-")
