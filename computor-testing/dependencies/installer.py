"""
Computor Framework - Dependency Installer

Command-line tool for installing dependencies from dependencies.yaml.
Can be used locally or in Docker build process.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from .models import Dependencies


def run_command(cmd: str, dry_run: bool = False, shell: bool = True) -> int:
    """Execute a shell command"""
    click.echo(f"  $ {cmd}")
    if dry_run:
        return 0
    result = subprocess.run(cmd, shell=shell)
    return result.returncode


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Computor Framework - Dependency Installer

    Install Python, R, Octave, and system dependencies from dependencies.yaml
    """
    pass


@cli.command()
@click.option("--file", "-f", "deps_file", type=click.Path(exists=True),
              default="dependencies.yaml", help="Path to dependencies.yaml")
@click.option("--python/--no-python", default=True, help="Install Python packages")
@click.option("--r/--no-r", "install_r", default=True, help="Install R packages")
@click.option("--octave/--no-octave", default=True, help="Install Octave packages")
@click.option("--system/--no-system", default=True, help="Install system packages")
@click.option("--dry-run", is_flag=True, help="Show commands without executing")
@click.option("--r-lib-path", type=str, default=None, help="R library path override")
def install(deps_file: str, python: bool, install_r: bool, octave: bool,
            system: bool, dry_run: bool, r_lib_path: Optional[str]):
    """Install all dependencies from dependencies.yaml"""

    click.secho(f"Loading dependencies from: {deps_file}", fg="cyan")
    deps = Dependencies.from_yaml(deps_file)

    errors = []

    # System packages first (often prerequisites for others)
    if system and deps.system:
        click.secho("\n=== Installing System Packages ===", fg="green", bold=True)
        if deps.system.apt:
            cmd = deps.system.to_apt_command()
            if run_command(cmd, dry_run) != 0:
                errors.append("System packages (apt)")

    # Python packages
    if python and deps.python:
        click.secho("\n=== Installing Python Packages ===", fg="green", bold=True)
        click.echo(f"Python version requirement: {deps.python.version}")

        for pkg_str in deps.python.to_pip_list():
            cmd = f"pip install '{pkg_str}'"
            if run_command(cmd, dry_run) != 0:
                errors.append(f"Python: {pkg_str}")

    # R packages
    if install_r and deps.r:
        click.secho("\n=== Installing R Packages ===", fg="green", bold=True)
        click.echo(f"R version requirement: {deps.r.version}")

        lib_path = r_lib_path or deps.r.lib_path
        if lib_path:
            click.echo(f"Library path: {lib_path}")
            os.makedirs(os.path.expanduser(lib_path), exist_ok=True)

        script = deps.r.to_install_script()

        # Write to temp file and execute
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            env = os.environ.copy()
            if lib_path:
                env['R_LIBS_USER'] = os.path.expanduser(lib_path)

            cmd = f"Rscript {script_path}"
            click.echo(f"  $ {cmd}")
            if not dry_run:
                result = subprocess.run(cmd, shell=True, env=env)
                if result.returncode != 0:
                    errors.append("R packages")
        finally:
            if not dry_run:
                os.unlink(script_path)

    # Octave packages
    if octave and deps.octave:
        click.secho("\n=== Installing Octave Packages ===", fg="green", bold=True)
        click.echo(f"Octave version requirement: {deps.octave.version}")

        script = deps.octave.to_install_script()

        for pkg in deps.octave.get_packages():
            cmd = f"octave --eval \"{pkg.to_install_command(deps.octave.forge)}\""
            if run_command(cmd, dry_run) != 0:
                errors.append(f"Octave: {pkg.name}")

    # Summary
    click.echo("")
    if errors:
        click.secho(f"Installation completed with {len(errors)} error(s):", fg="red")
        for err in errors:
            click.echo(f"  - {err}")
        sys.exit(1)
    else:
        click.secho("All dependencies installed successfully!", fg="green", bold=True)


@cli.command()
@click.option("--file", "-f", "deps_file", type=click.Path(exists=True),
              default="dependencies.yaml", help="Path to dependencies.yaml")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Output file (default: stdout)")
@click.option("--base-image", default="ubuntu:22.04", help="Base Docker image")
@click.option("--python-version", default="3.11", help="Python version")
@click.option("--include-r", is_flag=True, help="Include R installation")
@click.option("--include-octave", is_flag=True, help="Include Octave installation")
def dockerfile(deps_file: str, output: Optional[str], base_image: str,
               python_version: str, include_r: bool, include_octave: bool):
    """Generate Dockerfile from dependencies.yaml"""

    deps = Dependencies.from_yaml(deps_file)

    lines = [
        f"# Auto-generated from {deps_file}",
        f"FROM {base_image}",
        "",
        "# Prevent interactive prompts",
        "ENV DEBIAN_FRONTEND=noninteractive",
        "",
    ]

    # System packages
    system_pkgs = ["python3", "python3-pip", "python3-venv"]
    if include_r:
        system_pkgs.extend(["r-base", "r-base-dev"])
    if include_octave:
        system_pkgs.append("octave")

    if deps.system and deps.system.apt:
        system_pkgs.extend(deps.system.apt)

    lines.extend([
        "# System dependencies",
        "RUN apt-get update && apt-get install -y \\",
    ])
    for pkg in system_pkgs[:-1]:
        lines.append(f"    {pkg} \\")
    lines.append(f"    {system_pkgs[-1]} \\")
    lines.append("    && rm -rf /var/lib/apt/lists/*")
    lines.append("")

    # Python packages
    if deps.python:
        lines.extend([
            "# Python dependencies",
            "RUN pip3 install --no-cache-dir \\",
        ])
        pip_pkgs = deps.python.to_pip_list()
        for pkg in pip_pkgs[:-1]:
            lines.append(f"    '{pkg}' \\")
        lines.append(f"    '{pip_pkgs[-1]}'")
        lines.append("")

    # R packages
    if include_r and deps.r:
        cran_pkgs = [p.name for p in deps.r.get_packages()
                     if not (p.github or p.bioconductor)]
        if cran_pkgs:
            pkg_list = ", ".join(f"'{p}'" for p in cran_pkgs)
            lines.extend([
                "# R dependencies",
                f"RUN Rscript -e \"install.packages(c({pkg_list}), repos='https://cloud.r-project.org/')\"",
                "",
            ])

    # Octave packages
    if include_octave and deps.octave:
        lines.append("# Octave dependencies")
        for pkg in deps.octave.get_packages():
            lines.append(f"RUN octave --eval \"{pkg.to_install_command(deps.octave.forge)}\"")
        lines.append("")

    # Working directory
    lines.extend([
        "# Set working directory",
        "WORKDIR /app",
        "",
    ])

    content = "\n".join(lines)

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.secho(f"Dockerfile written to: {output}", fg="green")
    else:
        click.echo(content)


@cli.command()
@click.option("--file", "-f", "deps_file", type=click.Path(exists=True),
              default="dependencies.yaml", help="Path to dependencies.yaml")
@click.option("--format", "-F", "fmt", type=click.Choice(["pip", "r", "octave", "apt"]),
              required=True, help="Output format")
def export(deps_file: str, fmt: str):
    """Export dependencies in various formats"""

    deps = Dependencies.from_yaml(deps_file)

    if fmt == "pip":
        if deps.python:
            click.echo(deps.python.to_requirements_txt())
        else:
            click.echo("# No Python dependencies defined")

    elif fmt == "r":
        if deps.r:
            click.echo(deps.r.to_install_script())
        else:
            click.echo("# No R dependencies defined")

    elif fmt == "octave":
        if deps.octave:
            click.echo(deps.octave.to_install_script())
        else:
            click.echo("# No Octave dependencies defined")

    elif fmt == "apt":
        if deps.system and deps.system.apt:
            click.echo(" ".join(deps.system.apt))
        else:
            click.echo("# No apt dependencies defined")


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="merged-dependencies.yaml",
              help="Output file")
def merge(files: tuple, output: str):
    """Merge multiple dependencies.yaml files"""

    if not files:
        click.echo("No files specified", err=True)
        sys.exit(1)

    result = Dependencies()

    for path in files:
        click.echo(f"Loading: {path}")
        deps = Dependencies.from_yaml(path)
        result = result.merge(deps)

    with open(output, "w") as f:
        f.write(result.to_yaml())

    click.secho(f"Merged dependencies written to: {output}", fg="green")


@cli.command()
@click.option("--file", "-f", "deps_file", type=click.Path(exists=True),
              default="dependencies.yaml", help="Path to dependencies.yaml")
def validate(deps_file: str):
    """Validate dependencies.yaml syntax"""

    try:
        deps = Dependencies.from_yaml(deps_file)
        click.secho(f"✓ {deps_file} is valid", fg="green")

        # Summary
        if deps.python:
            click.echo(f"  Python packages: {len(deps.python.packages)}")
        if deps.r:
            click.echo(f"  R packages: {len(deps.r.packages)}")
        if deps.octave:
            click.echo(f"  Octave packages: {len(deps.octave.packages)}")
        if deps.system:
            click.echo(f"  System packages (apt): {len(deps.system.apt)}")

    except Exception as e:
        click.secho(f"✗ Validation failed: {e}", fg="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
