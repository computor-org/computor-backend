"""Upload VSIX extensions defined in the deployment configuration."""

from pathlib import Path

import click

from computor_cli.auth import get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async

from computor_utils.vsix_utils import parse_vsix_metadata
from computor_types.exceptions import VsixManifestError


def _upload_extensions_from_config(entries: list, config_dir: Path, auth: CLIAuthConfig, client):
    """Upload VSIX extensions defined in the deployment configuration."""


    client = run_async(get_computor_client(auth))

    for entry in entries:
        entry_path = Path(entry.path)
        resolved_path = entry_path if entry_path.is_absolute() else (config_dir / entry_path).resolve()

        click.echo(f"\n📦 Extension package: {resolved_path}")

        if not resolved_path.exists() or not resolved_path.is_file():
            click.echo(f"  ❌ File not found: {resolved_path}", err=True)
            continue

        try:
            file_bytes = resolved_path.read_bytes()
        except OSError as exc:
            click.echo(f"  ❌ Could not read VSIX file: {exc}", err=True)
            continue

        try:
            manifest = parse_vsix_metadata(file_bytes)
        except VsixManifestError as exc:
            click.echo(f"  ❌ Invalid VSIX package: {exc}", err=True)
            continue

        publisher = entry.publisher or manifest.publisher
        name = entry.name or manifest.name
        identity = f"{publisher}.{name}"
        version = manifest.version

        click.echo(f"  ➡️  Uploading {identity}@{version}")

        engine_range = entry.engine_range or manifest.engine_range
        display_name = entry.display_name or manifest.display_name
        description = entry.description if entry.description is not None else manifest.description

        form_data = {"version": version}
        if engine_range:
            form_data["engine_range"] = engine_range
        if display_name:
            form_data["display_name"] = display_name
        if description:
            form_data["description"] = description

        form_data = {key: str(value) for key, value in form_data.items() if value is not None}

        try:
            # Use the underlying httpx client for multipart/form-data upload
            # Note: client._http is async, so we need to use the sync httpx client
            import httpx
            import io

            # Create file-like object for httpx
            file_obj = io.BytesIO(file_bytes)
            files = {
                "file": (resolved_path.name, file_obj, "application/octet-stream")
            }

            # Multipart upload: the sync facade only sends JSON, so use raw
            # httpx here, but take auth headers from the public accessor and
            # drop Content-Type so httpx sets the multipart boundary.
            headers = dict(client.auth_headers)
            headers.pop('content-type', None)
            headers.pop('Content-Type', None)

            with httpx.Client(base_url=client.base_url, headers=headers) as sync_client:
                response = sync_client.post(
                    f"extensions/{identity}/versions",
                    data=form_data,
                    files=files,
                )
                if response.status_code != 201:
                    click.echo(f"  ❌ Upload failed: HTTP {response.status_code}", err=True)
                    click.echo(f"  Response: {response.text}", err=True)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            click.echo(f"  ❌ Upload failed: {exc}", err=True)
            continue

        uploaded_version = payload.get("version", version)
        sha256 = payload.get("sha256", "<unknown>")
        click.echo(f"  ✅ Uploaded version {uploaded_version} (sha256 {sha256})")
