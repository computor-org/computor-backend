"""The upload limiter bounds the body bytes actually received.

A chunked request carries no Content-Length, so a header-only check let it
through to multipart parsing, which spools the whole body before any
authentication or validation runs.
"""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from computor_backend.middleware.upload_limiter import UploadSizeLimiterMiddleware

MIB = 1024 * 1024


def _app():
    app = FastAPI()
    seen = {"bytes": None}

    @app.post("/raw")
    async def raw(request: Request):
        seen["bytes"] = len(await request.body())
        return {"ok": True}

    # max_size=0 -> limit is the 1 MiB metadata allowance
    app.add_middleware(UploadSizeLimiterMiddleware, max_size=0)
    return app, seen


def _chunks(total, size=64 * 1024):
    sent = 0
    while sent < total:
        n = min(size, total - sent)
        sent += n
        yield b"x" * n


def test_chunked_body_over_the_limit_is_413_and_never_reaches_the_handler():
    app, seen = _app()
    r = TestClient(app).post("/raw", content=_chunks(3 * MIB))
    assert r.status_code == 413
    assert seen["bytes"] is None


def test_chunked_body_under_the_limit_passes():
    app, seen = _app()
    r = TestClient(app).post("/raw", content=_chunks(MIB // 2))
    assert r.status_code == 200
    assert seen["bytes"] == MIB // 2


def test_understated_content_length_is_still_bounded():
    app, seen = _app()
    r = TestClient(app).post(
        "/raw", content=_chunks(3 * MIB), headers={"Content-Length": "10"}
    )
    assert r.status_code == 413
    assert seen["bytes"] is None


def test_declared_oversize_content_length_is_refused_up_front():
    app, seen = _app()
    r = TestClient(app).post("/raw", content=b"x" * (2 * MIB))
    assert r.status_code == 413
    assert seen["bytes"] is None


def test_real_app_multipart_upload_chunked_over_limit_is_413():
    from computor_backend.server import app
    from computor_backend.storage_config import MAX_UPLOAD_SIZE

    boundary = b"b0undary"
    head = (
        b"--" + boundary + b'\r\nContent-Disposition: form-data; name="file"; '
        b'filename="a.bin"\r\nContent-Type: application/octet-stream\r\n\r\n'
    )

    def body():
        yield head
        yield from _chunks(MAX_UPLOAD_SIZE + 2 * MIB, size=MIB)
        yield b"\r\n--" + boundary + b"--\r\n"

    r = TestClient(app).post(
        "/storage/upload",
        content=body(),
        headers={"Content-Type": "multipart/form-data; boundary=b0undary"},
    )
    assert r.status_code == 413
