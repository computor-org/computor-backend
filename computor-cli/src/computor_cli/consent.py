"""GDPR privacy-notice (consent policy) commands.

Publish and inspect the versioned privacy notices that back the consent gate.
A notice lives on disk as a ``data/consent/<version>/`` directory holding one
``{lang}.md`` Markdown file per language (plus an optional ``policy.yaml`` for
``effective_from`` / ``version`` / ``languages``). Publishing POSTs it to
``/consent/policy-versions`` (admin only, append-only/write-once).

See ``data/consent/README.md`` for the on-disk format.
"""

from datetime import datetime
from pathlib import Path

import click
import httpx
import yaml

from computor_cli.auth import authenticate


def _load_policy_dir(path: Path):
    """Read a ``data/consent/<version>/`` directory.

    Returns ``(version, effective_from, texts)`` where ``texts`` maps a language
    code to its Markdown notice. ``version`` defaults to the directory name and
    ``effective_from`` to whatever ``policy.yaml`` declares (may be ``None``).
    """
    meta = {}
    meta_file = path / "policy.yaml"
    if meta_file.exists():
        meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}

    version = str(meta.get("version") or path.name)
    effective_from = meta.get("effective_from")

    languages = meta.get("languages")
    texts: dict[str, str] = {}
    if languages:
        for lang in languages:
            f = path / f"{lang}.md"
            if not f.exists():
                raise click.ClickException(
                    f"policy.yaml declares language '{lang}' but {f.name} is missing in {path}"
                )
            texts[lang] = f.read_text(encoding="utf-8")
    else:
        for f in sorted(path.glob("*.md")):
            if f.name.lower() == "readme.md":
                continue
            texts[f.stem] = f.read_text(encoding="utf-8")

    if not texts:
        raise click.ClickException(f"No language Markdown files ('*.md') found in {path}")

    return version, effective_from, texts


def _err_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        return body.get("detail") or body.get("error") or resp.text
    except Exception:
        return resp.text


def _api_client(auth) -> httpx.Client:
    """Authenticated httpx client, or a clean error if no token is configured.

    ``@authenticate`` only guarantees a profile *file* exists; it may still carry
    no token, so guard here rather than letting httpx crash on a None header.
    """
    if not auth.token:
        click.secho("Not logged in. Run 'computor login' with an admin API token.", fg="red", err=True)
        raise SystemExit(1)
    return httpx.Client(base_url=auth.api_url, headers={"X-API-Token": auth.token}, timeout=30.0)


@click.group()
def consent():
    """Publish and inspect GDPR privacy-notice (consent policy) versions."""
    pass


@consent.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--effective-from",
    "effective_from",
    default=None,
    help="ISO datetime when the version becomes current (overrides policy.yaml; "
    "default: now). A future value schedules the version.",
)
@click.option("--dry-run", is_flag=True, help="Show what would be published without calling the API.")
@authenticate
def publish(path: Path, effective_from, dry_run, auth):
    """Publish a privacy notice version from a data/consent/<version>/ directory.

    Reads the {lang}.md files (and optional policy.yaml) and POSTs them to
    /consent/policy-versions. Requires the _admin role. Append-only: a version
    can be published exactly once; effective_from <= now re-gates every user who
    has not consented to the new version.

    \b
    Examples:
        ctutor consent publish data/consent/2026-07-05
        ctutor consent publish data/consent/2026-07-05 --dry-run
        ctutor consent publish data/consent/2026-07-05 --effective-from 2026-08-01T00:00:00Z
    """
    version, meta_effective, texts = _load_policy_dir(path)
    eff = effective_from if effective_from is not None else meta_effective

    payload: dict = {"version": version, "texts": texts}
    if eff not in (None, ""):
        payload["effective_from"] = eff.isoformat() if isinstance(eff, datetime) else str(eff)

    click.echo(f"Version:        {version}")
    click.echo(f"Effective from: {payload.get('effective_from', 'now')}")
    click.echo(
        "Languages:      "
        + ", ".join(f"{lang} ({len(md)} chars)" for lang, md in sorted(texts.items()))
    )

    if dry_run:
        click.secho("\n[dry-run] Nothing published.", fg="yellow")
        return

    try:
        with _api_client(auth) as client:
            resp = client.post("/consent/policy-versions", json=payload)
    except httpx.HTTPError as e:
        click.secho(f"Error contacting {auth.api_url}: {e}", fg="red", err=True)
        raise SystemExit(1)

    if resp.status_code == 201:
        data = resp.json()
        click.secho(
            f"\n✅ Published policy version '{data['version']}' "
            f"(effective {data.get('effective_from')}).",
            fg="green",
            bold=True,
        )
        click.echo(f"   languages: {', '.join(data.get('languages') or [])}")
        click.secho(
            "   ⚠  Users without consent for this version are now gated on their next request.",
            fg="yellow",
        )
        return

    if resp.status_code == 403:
        click.secho("Error: publishing a policy version requires the _admin role.", fg="red", err=True)
    elif resp.status_code == 401:
        click.secho("Error: not authenticated. Run 'computor login' with an admin token.", fg="red", err=True)
    else:
        click.secho(f"Error {resp.status_code}: {_err_detail(resp)}", fg="red", err=True)
    raise SystemExit(1)


@consent.command("list")
@authenticate
def list_versions(auth):
    """List published privacy notice versions (admin)."""
    try:
        with _api_client(auth) as client:
            resp = client.get("/consent/policy-versions")
    except httpx.HTTPError as e:
        click.secho(f"Error contacting {auth.api_url}: {e}", fg="red", err=True)
        raise SystemExit(1)

    if resp.status_code == 403:
        click.secho("Error: listing policy versions requires the _admin role.", fg="red", err=True)
        raise SystemExit(1)
    if resp.status_code != 200:
        click.secho(f"Error {resp.status_code}: {_err_detail(resp)}", fg="red", err=True)
        raise SystemExit(1)

    versions = resp.json()
    if not versions:
        click.echo("No policy versions published yet.")
        return

    click.echo(f"\n{'Version':<20} {'Effective from':<28} {'Languages':<16} {'Created':<20}")
    click.echo("-" * 84)
    for v in versions:
        langs = ", ".join(v.get("languages") or [])
        created = str(v.get("created_at") or "")[:19]
        click.echo(f"{v['version']:<20} {str(v.get('effective_from') or ''):<28} {langs:<16} {created:<20}")
    click.echo()


if __name__ == "__main__":
    consent()
