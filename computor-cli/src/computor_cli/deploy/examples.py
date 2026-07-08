"""Upload examples (dependency-ordered) to an example repository."""

import io
import base64
import zipfile
from pathlib import Path

import yaml
import click

from computor_cli.auth import get_computor_client
from computor_client import SyncComputorClient
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async


def _ensure_example_repository(repo_name: str, auth: CLIAuthConfig):
    """Find or create an example repository with MinIO backend."""

    # Use direct HTTP client to avoid pydantic validation issues
    # The generated client tries to validate list responses as ExampleRepositoryGet
    # but the API returns ExampleRepositoryList which doesn't have created_at/updated_at
    import httpx

    async def _find_or_create_repo():
        async with httpx.AsyncClient(base_url=auth.api_url) as http_client:
            # Authenticate
            if auth.token:
                http_client.headers.update({"X-API-Token": auth.token})

            # Search for existing repository
            click.echo(f"    🔍 Searching for repository: {repo_name}")
            response = await http_client.get("/example-repositories", params={"name": repo_name})
            response.raise_for_status()

            repos = response.json()
            click.echo(f"    🔍 Found {len(repos)} matching repositories")

            from types import SimpleNamespace

            if repos:
                repo = repos[0]
                click.echo(f"    ✅ Using existing repository: {repo['name']} (ID: {repo['id']}, source_url: {repo['source_url']})")
                return SimpleNamespace(**repo)

            # Create new repository
            click.echo(f"    📦 Creating new repository: {repo_name}")
            create_data = {
                "name": repo_name,
                "description": f"Repository for {repo_name} examples",
                "source_type": "minio",
                "source_url": "examples-bucket",
            }

            response = await http_client.post("/example-repositories", json=create_data)
            response.raise_for_status()

            repo = response.json()
            click.echo(f"    ✅ Created repository: {repo['name']} (ID: {repo['id']})")
            return SimpleNamespace(**repo)

    return run_async(_find_or_create_repo())


def _create_zip_bytes_from_directory(directory_path: Path) -> bytes:
    """Create a zip archive from a directory; ensure meta.yaml exists.

    - Skips hidden files/dirs (starting with '.')
    - If meta.yaml is missing, generates a minimal one
    """
    # Determine if meta.yaml exists
    meta_path = directory_path / "meta.yaml"
    needs_meta = not meta_path.is_file()

    # Prepare in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        # Add all non-hidden files recursively
        for file_path in directory_path.rglob("*"):
            rel = file_path.relative_to(directory_path)
            # Skip hidden files/dirs
            parts = rel.parts
            if any(part.startswith(".") for part in parts):
                continue
            if file_path.is_file():
                zipf.write(file_path, arcname=str(rel))

        # Inject minimal meta.yaml if missing
        if needs_meta:
            minimal_meta = (
                "title: "
                + directory_path.name.replace('-', ' ').replace('_', ' ').title()
                + "\n"
                + f"description: Example from {directory_path.name}\n"
                + "language: en\n"
            )
            zipf.writestr("meta.yaml", minimal_meta)

    return zip_buffer.getvalue()


def _read_meta_and_dependencies(example_dir: Path) -> tuple[str, list[str]]:
    """Read meta.yaml from a directory and return (slug, dependencies).

    - Slug comes from meta.yaml 'slug' or falls back to directory name mapped to dots
    - Dependencies are read from either 'properties.testDependencies' or 'testDependencies'
      and normalized to a list of slugs
    """
    meta_path = example_dir / "meta.yaml"
    slug = example_dir.name.replace('-', '.').replace('_', '.')
    dependencies: list[str] = []

    if meta_path.is_file():
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            meta = {}
        slug = meta.get('slug', slug)

        # testDependencies can be in meta['properties']['testDependencies'] or meta['testDependencies']
        td = None
        if isinstance(meta.get('properties'), dict) and 'testDependencies' in meta['properties']:
            td = meta['properties'].get('testDependencies')
        elif 'testDependencies' in meta:
            td = meta.get('testDependencies')

        if isinstance(td, list):
            for item in td:
                if isinstance(item, str):
                    dependencies.append(item)
                elif isinstance(item, dict) and 'slug' in item:
                    dependencies.append(item['slug'])
    return slug, dependencies


def _toposort_by_dependencies(subdirs: list[Path]) -> list[Path]:
    """Topologically sort example directories so dependencies come first.

    - Builds a graph based on meta.yaml testDependencies slugs
    - Only considers dependencies that are present in the batch
    - On cycles, falls back to appending remaining nodes in stable order
    """
    # Build slug mapping and deps
    slug_to_dir: dict[str, Path] = {}
    deps_map: dict[str, set[str]] = {}

    for d in subdirs:
        slug, deps = _read_meta_and_dependencies(d)
        slug_to_dir[slug] = d
        deps_map[slug] = set(deps)

    # Reduce dependencies to only those within this batch
    for slug, deps in deps_map.items():
        deps_map[slug] = set(dep for dep in deps if dep in slug_to_dir)

    # Compute in-degrees
    in_degree: dict[str, int] = {slug: 0 for slug in slug_to_dir}
    for slug, deps in deps_map.items():
        for dep in deps:
            in_degree[slug] += 1

    # Kahn's algorithm
    queue = [slug for slug, deg in in_degree.items() if deg == 0]
    queue.sort()  # stable order
    ordered_slugs: list[str] = []

    # Build reverse edges: dep -> [slug]
    rev: dict[str, set[str]] = {s: set() for s in slug_to_dir}
    for slug, deps in deps_map.items():
        for dep in deps:
            rev[dep].add(slug)

    while queue:
        s = queue.pop(0)
        ordered_slugs.append(s)
        for nxt in sorted(rev.get(s, [])):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    # If there are nodes left (cycle), append them in deterministic order
    if len(ordered_slugs) < len(slug_to_dir):
        remaining = [s for s in slug_to_dir if s not in ordered_slugs]
        ordered_slugs.extend(sorted(remaining))

    return [slug_to_dir[s] for s in ordered_slugs]


def _upload_examples_from_directory(examples_dir: Path, repo_name: str, auth: CLIAuthConfig, client):
    """Upload each subdirectory in examples_dir as a zipped example to the API.

    The upload order is topologically sorted by dependencies found in meta.yaml.
    """

    client = run_async(get_computor_client(auth))
    custom_client = SyncComputorClient.from_client(client)

    if not examples_dir.exists() or not examples_dir.is_dir():
        click.echo(f"⚠️  Examples directory not found or not a directory: {examples_dir}")
        return

    # Ensure repository exists
    repo = _ensure_example_repository(repo_name, auth)
    repo_id = str(repo.id)

    # Collect immediate subdirectories
    subdirs = [d for d in examples_dir.iterdir() if d.is_dir()]
    if not subdirs:
        click.echo(f"ℹ️  No example subdirectories found in {examples_dir}")
        return

    # Sort by dependencies so prerequisites upload first
    ordered_subdirs = _toposort_by_dependencies(subdirs)

    click.echo(f"\n📦 Uploading {len(ordered_subdirs)} example(s) from '{examples_dir}' to repository '{repo_name}'...")

    uploaded = 0
    failed = 0
    for subdir in ordered_subdirs:
        try:
            # Create zip bytes (ensure meta.yaml is included)
            zip_bytes = _create_zip_bytes_from_directory(subdir)
            b64_zip = base64.b64encode(zip_bytes).decode("ascii")

            payload = {
                "repository_id": repo_id,
                "directory": subdir.name,
                "files": {f"{subdir.name}.zip": b64_zip},
            }

            # Upload
            custom_client.create("examples/upload", payload)
            click.echo(f"  ✅ Uploaded example: {subdir.name}")
            uploaded += 1
        except Exception as e:
            click.echo(f"  ❌ Failed to upload {subdir.name}: {e}")
            failed += 1

    click.echo(f"📊 Example upload summary — success: {uploaded}, failed: {failed}, total: {len(subdirs)}")
