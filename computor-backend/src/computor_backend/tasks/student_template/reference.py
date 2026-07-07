"""Staff-only reference repository (solution mirror of the student template)."""
import logging
from pathlib import Path

from ..git_ops import clone_or_init, commit_and_push, configure_identity

logger = logging.getLogger(__name__)

# When True, the reference repo receives a verbatim copy of the WHOLE example
# (the original behavior — solutions, localTests/, content/, everything). When
# False (default), it receives a template-like layout via
# ``process_example_for_reference_v2`` below: README from content/index,
# additionalFiles, studentSubmissionFiles filled with the SOLUTION, plus
# meta.yaml/test.yaml. The whole-copy path is kept (flag-gated) so the original
# behavior is one switch away, not deleted.
REFERENCE_INCLUDE_FULL_EXAMPLE = False


def process_example_for_reference_v2(example_files, target_path, additional_files, submission_files):
    """Staff **reference** variant of the student-template converter.

    Same layout as ``process_example_for_student_template_v2`` — ``content/index*.md``
    renamed to ``README*.md``, ``additionalFiles`` copied to the assignment root —
    but ``studentSubmissionFiles`` are filled with the **solution** content (the
    example's own file at the submission path, else its ``localTests/correctSolution``
    copy) instead of the emptied student template, and ``meta.yaml``/``test.yaml``
    are exposed (staff-only). Synchronous; the caller (`push_reference_repo`) is sync.
    """
    target_path.mkdir(parents=True, exist_ok=True)

    # content/index*.md -> README*.md and content/mediaFiles/** -> mediaFiles/**
    # (identical to the template — the README's relative image links resolve).
    for filename, data in example_files.items():
        if filename == "content/index.md":
            (target_path / "README.md").write_bytes(data)
        elif filename.startswith("content/index_") and filename.endswith(".md"):
            lang_suffix = filename[len("content/index"):-3]  # '_de' from 'content/index_de.md'
            (target_path / f"README{lang_suffix}.md").write_bytes(data)
        elif filename.startswith("content/mediaFiles/"):
            dest = target_path / filename[len("content/"):]  # 'mediaFiles/foo.png'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

    # additionalFiles -> assignment root (identical to the template).
    for file_name in additional_files:
        if file_name in example_files:
            fp = target_path / Path(file_name).name
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_bytes(example_files[file_name])

    # studentSubmissionFiles -> the SOLUTION content (the reference difference).
    for submission_file in submission_files:
        sp = target_path / submission_file
        sp.parent.mkdir(parents=True, exist_ok=True)
        candidates = [
            submission_file,                                          # author's canonical solution at the submission path
            f"localTests/correctSolution/{submission_file}",         # correct-solution copy used by tests
            f"localTests/correctSolution/{Path(submission_file).name}",
        ]
        data = next((example_files[c] for c in candidates if c in example_files), None)
        if data is None:
            # Last resort: match by filename, preferring a non-studentTemplate path.
            name = Path(submission_file).name
            data = next(
                (d for p, d in example_files.items() if Path(p).name == name and "studentTemplate" not in p),
                None,
            )
        sp.write_bytes(data if data is not None else b"")

    # Expose meta.yaml + test.yaml (staff-only reference).
    for meta_name in ("meta.yaml", "test.yaml"):
        if meta_name in example_files:
            (target_path / meta_name).write_bytes(example_files[meta_name])


def push_reference_repo(binding, reference_files, gitlab_token, server_type):
    """Push the course's staff-only reference repo — the solution mirror of the
    student template. By default each assignment gets a template-like layout with
    the SOLUTION filled in (see ``process_example_for_reference_v2``); the legacy
    verbatim whole-example copy is available via ``REFERENCE_INCLUDE_FULL_EXAMPLE``.

    Best-effort: the caller wraps this in try/except so a reference-push failure
    never affects the student-template deploy (the student-facing artifact). The
    reference repo ref comes from the course git binding
    (``properties.gitlab.reference_path`` for GitLab, ``properties.forgejo.reference_repo``
    for Forgejo); credentials are the same per-course binding token as the template.
    """
    import tempfile
    import os

    if binding is None or binding.git_server is None or not reference_files:
        return
    props = binding.properties or {}
    reference_ref = (
        (props.get("gitlab") or {}).get("reference_path")
        or (props.get("forgejo") or {}).get("reference_repo")
    )
    if not reference_ref:
        logger.info("No reference repo configured for this course; skipping reference push")
        return

    from ...git_provider import backend_reachable_base_url

    public_base = (binding.git_server.base_url or "").rstrip("/")
    reachable_base = backend_reachable_base_url(binding.git_server)
    reference_url = f"{public_base}/{reference_ref}.git"
    push_url = reference_url
    if reachable_base and reachable_base != public_base and reference_url.startswith(public_base):
        push_url = reachable_base + reference_url[len(public_base):]

    with tempfile.TemporaryDirectory() as ref_temp:
        ref_path = os.path.join(ref_temp, "reference")
        repo = clone_or_init(push_url, gitlab_token, server_type, ref_path)
        configure_identity(repo)

        # Write each assignment's reference content. Default = a template-like
        # layout (README from content/index, additionalFiles, studentSubmissionFiles
        # filled with the SOLUTION) plus meta.yaml/test.yaml. The legacy verbatim
        # whole-example copy is kept, flag-gated by REFERENCE_INCLUDE_FULL_EXAMPLE.
        for target_dir, tgt in reference_files.items():
            files = tgt["files"]
            if REFERENCE_INCLUDE_FULL_EXAMPLE:
                for rel_path, data in files.items():
                    dest = os.path.join(ref_path, target_dir, rel_path)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as fh:
                        fh.write(data if isinstance(data, (bytes, bytearray)) else str(data).encode())
            else:
                process_example_for_reference_v2(
                    files,
                    Path(os.path.join(ref_path, target_dir)),
                    tgt.get("additional_files") or [],
                    tgt.get("submission_files") or [],
                )

        with open(os.path.join(ref_path, "README.md"), "w") as fh:
            fh.write(
                "# Reference (full solutions)\n\n"
                "Staff-only. Mirrors the student template's assignments with the "
                "complete example content (solutions included). Generated by Computor.\n"
            )

        commit_and_push(repo, "System Reference")
