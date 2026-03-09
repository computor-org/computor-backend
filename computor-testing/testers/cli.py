"""
Unified CLI for Computor Testing Framework

Provides a single entry point for all language testers.

Usage:
    computor-test python run -t student/ -T test.yaml
    computor-test octave run -t student/ -T test.yaml
    computor-test check python
    computor-test check --all
"""

import sys
import click

from . import list_testers, normalize_language
from .base import get_tester, TESTERS
from .executors import EXECUTORS


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Computor Testing Framework

    A unified testing framework for multiple programming languages.

    Supported languages: python, octave, r, julia, c, fortran, document
    """
    pass


# Dynamic language subcommands
def create_language_cli(language: str):
    """Create a CLI group for a specific language."""

    @click.group(name=language)
    def lang_cli():
        f"""Testing commands for {language.title()}"""
        pass

    @lang_cli.command()
    @click.option("--target", "-t", type=click.Path(exists=True),
                  help="Target directory containing student code")
    @click.option("--test", "-T", "testsuite", type=click.Path(exists=True),
                  required=True, help="Path to test.yaml file")
    @click.option("--specification", "-s", type=click.Path(exists=True),
                  help="Path to specification.yaml file")
    @click.option("--pytestflags", "-p", default="",
                  help="Additional flags to pass to pytest")
    @click.option("--verbosity", "-v", default=0, type=int,
                  help="Verbosity level (0-3)")
    def run(target, testsuite, specification, pytestflags, verbosity):
        """Run tests on target directory."""
        tester_class = get_tester(language)
        if not tester_class:
            click.secho(f"Error: No tester for language: {language}", fg="red", err=True)
            sys.exit(1)

        import os
        testroot = os.path.dirname(os.path.abspath(testsuite))
        tester = tester_class(testroot=testroot)

        exit_code = tester.run(
            target=target,
            testsuite=testsuite,
            specification=specification,
            pytestflags=pytestflags,
            verbosity=verbosity,
        )
        sys.exit(exit_code)

    @lang_cli.command()
    @click.option("-d", "--directory", type=click.Path(exists=True),
                  required=True, help="Directory containing solution")
    @click.option("-v", "--verbosity", default=1, type=int,
                  help="Verbosity level (0-3)")
    def local(directory, verbosity):
        """Run local tests in directory."""
        tester_class = get_tester(language)
        if not tester_class:
            click.secho(f"Error: No tester for language: {language}", fg="red", err=True)
            sys.exit(1)

        tester = tester_class()
        exit_code = tester.local(directory, verbosity)
        sys.exit(exit_code)

    @lang_cli.command()
    def check():
        """Check if runtime is installed."""
        executor_class = EXECUTORS.get(language)
        if not executor_class:
            click.secho(f"Error: No executor for language: {language}", fg="red", err=True)
            sys.exit(1)

        installed, info = executor_class.check_installed()
        if installed:
            click.secho(f"{language.title()} is installed", fg="green")
            click.echo(f"  Version: {info}")
        else:
            click.secho(f"{language.title()} is not available", fg="red")
            click.echo(f"  Error: {info}")
            sys.exit(1)

    return lang_cli


# Register language subcommands
for lang in list_testers():
    cli.add_command(create_language_cli(lang))


@cli.command()
@click.option("--all", "-a", "check_all", is_flag=True,
              help="Check all languages")
@click.argument("language", required=False)
def check(check_all, language):
    """Check if language runtimes are installed.

    Examples:
        computor-test check python
        computor-test check --all
    """
    if check_all:
        click.echo("Checking all language runtimes:")
        click.echo()
        all_ok = True
        for lang in list_testers():
            executor_class = EXECUTORS.get(lang)
            if executor_class:
                installed, info = executor_class.check_installed()
                status = click.style("✓", fg="green") if installed else click.style("✗", fg="red")
                click.echo(f"  {status} {lang:10} {info[:50]}...")
                if not installed:
                    all_ok = False
        if not all_ok:
            sys.exit(1)
    elif language:
        lang = normalize_language(language)
        if not lang:
            click.secho(f"Error: Unknown language: {language}", fg="red", err=True)
            click.echo(f"Available: {', '.join(list_testers())}")
            sys.exit(1)

        executor_class = EXECUTORS.get(lang)
        if not executor_class:
            click.secho(f"Error: No executor for language: {lang}", fg="red", err=True)
            sys.exit(1)

        installed, info = executor_class.check_installed()
        if installed:
            click.secho(f"{lang.title()} is installed", fg="green")
            click.echo(f"  Version: {info}")
        else:
            click.secho(f"{lang.title()} is not available", fg="red")
            click.echo(f"  Error: {info}")
            sys.exit(1)
    else:
        click.echo("Usage: computor-test check [--all | LANGUAGE]")
        click.echo(f"Available languages: {', '.join(list_testers())}")


@cli.command("list")
def list_cmd():
    """List available testers and their status."""
    click.echo("Available testers:")
    click.echo()
    for lang in list_testers():
        executor_class = EXECUTORS.get(lang)
        if executor_class:
            installed, info = executor_class.check_installed()
            status = click.style("✓", fg="green") if installed else click.style("✗", fg="red")
            click.echo(f"  {status} {lang:10} - {info[:50]}")
        else:
            click.echo(f"  ? {lang:10} - No executor")


# Language-specific CLI entry points
def pytester_cli():
    """Python tester CLI."""
    from .runners import PythonTester
    _legacy_cli(PythonTester)


def octester_cli():
    """Octave tester CLI."""
    from .runners import OctaveTester
    _legacy_cli(OctaveTester)


def rtester_cli():
    """R tester CLI."""
    from .runners import RTester
    _legacy_cli(RTester)


def jltester_cli():
    """Julia tester CLI."""
    from .runners import JuliaTester
    _legacy_cli(JuliaTester)


def ctester_cli():
    """C/C++ tester CLI."""
    from .runners import CTester
    _legacy_cli(CTester)


def ftester_cli():
    """Fortran tester CLI."""
    from .runners import FortranTester
    _legacy_cli(FortranTester)


def doctester_cli():
    """Document tester CLI."""
    from .runners import DocumentTester
    _legacy_cli(DocumentTester)


def _legacy_cli(tester_class):
    """Create a legacy-compatible CLI."""
    import os

    @click.group()
    @click.version_option(version="0.1.0")
    def legacy():
        f"""{tester_class.language.title()} Testing Framework"""
        pass

    @legacy.command()
    @click.option("--target", "-t", type=click.Path(exists=True),
                  help="Target directory containing student code")
    @click.option("--test", "-T", "testsuite", type=click.Path(exists=True),
                  required=True, help="Path to test.yaml file")
    @click.option("--specification", "-s", type=click.Path(exists=True),
                  help="Path to specification.yaml file")
    @click.option("--pytestflags", "-p", default="",
                  help="Additional flags to pass to pytest")
    @click.option("--verbosity", "-v", default=0, type=int,
                  help="Verbosity level (0-3)")
    def run(target, testsuite, specification, pytestflags, verbosity):
        """Run tests on target directory."""
        testroot = os.path.dirname(os.path.abspath(testsuite))
        tester = tester_class(testroot=testroot)
        exit_code = tester.run(
            target=target,
            testsuite=testsuite,
            specification=specification,
            pytestflags=pytestflags,
            verbosity=verbosity,
        )
        sys.exit(exit_code)

    @legacy.command()
    @click.option("-d", "--directory", type=click.Path(exists=True),
                  required=True, help="Directory containing solution")
    def local(directory):
        """Run local tests in directory."""
        tester = tester_class()
        exit_code = tester.local(directory)
        sys.exit(exit_code)

    @legacy.command()
    def check():
        """Check if runtime is installed."""
        installed, info = tester_class().check_installed()
        if installed:
            click.secho(f"{tester_class.language.title()} is installed", fg="green")
            click.echo(f"  Version: {info}")
        else:
            click.secho(f"{tester_class.language.title()} is not available", fg="red")
            click.echo(f"  Error: {info}")
            sys.exit(1)

    legacy()


if __name__ == "__main__":
    cli()
