"""
Runner CLI

Command-line interface for runner configuration and testing.
"""

import sys
import click

from .config import (
    RunnerBackend,
    RunnerSettings,
    check_backend_available,
    get_available_backends,
    get_best_available_backend,
    get_settings,
    configure,
)
from .backends import get_runner


@click.group()
@click.version_option(version="0.1.0", prog_name="sandbox")
def cli():
    """Computor Testing Framework - Runner Configuration

    Configure and test execution backends.

    Examples:

        sandbox check              # Check available backends
        sandbox run python3 -c "print('hello')"
        sandbox config --backend docker
    """
    pass


@cli.command("check")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
def check_backends(verbose):
    """Check which execution backends are available.

    Examples:

        sandbox check
        sandbox check -v
    """
    click.echo("Checking available backends...\n")

    available = []
    unavailable = []

    for backend in RunnerBackend:
        is_available, message = check_backend_available(backend)

        if is_available:
            available.append((backend, message))
            status = click.style("✓", fg="green")
        else:
            unavailable.append((backend, message))
            status = click.style("✗", fg="red")

        name = click.style(backend.value.ljust(12), bold=True)
        click.echo(f"  {status} {name} {message if verbose else ''}")

    click.echo()

    best = get_best_available_backend()
    click.echo(f"Recommended backend: {click.style(best.value, fg='cyan', bold=True)}")

    current = get_settings().backend
    click.echo(f"Current backend: {click.style(current.value, fg='yellow')}")


@cli.command("config")
@click.option("-b", "--backend", type=click.Choice([b.value for b in RunnerBackend]),
              help="Execution backend to use")
@click.option("-t", "--timeout", type=float, help="Execution timeout in seconds")
@click.option("-m", "--memory", type=int, help="Memory limit in MB")
@click.option("--network/--no-network", default=None, help="Enable/disable network access")
@click.option("--show", is_flag=True, help="Show current configuration")
def config_runner(backend, timeout, memory, network, show):
    """Configure runner settings.

    Examples:

        sandbox config --show
        sandbox config --backend docker --timeout 30
        sandbox config --backend local --no-network
    """
    if show or (backend is None and timeout is None and memory is None and network is None):
        settings = get_settings()
        click.echo("Current runner configuration:\n")

        data = settings.to_dict()
        for key, value in data.items():
            if value is not None and value != [] and value != {}:
                click.echo(f"  {click.style(key, fg='cyan')}: {value}")
        return

    # Apply configuration
    kwargs = {}
    if backend:
        kwargs['backend'] = backend
    if timeout:
        kwargs['timeout'] = timeout
    if memory:
        kwargs['memory_mb'] = memory
    if network is not None:
        kwargs['network'] = network

    try:
        settings = configure(**kwargs)
        click.echo(click.style("Configuration updated:", fg="green"))
        click.echo(f"  Backend: {settings.backend.value}")
        click.echo(f"  Timeout: {settings.timeout}s")
        click.echo(f"  Memory: {settings.memory_mb}MB")
        click.echo(f"  Network: {'enabled' if settings.network_enabled else 'disabled'}")
    except ValueError as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command("run")
@click.argument("command", nargs=-1, required=True)
@click.option("-b", "--backend", type=click.Choice([b.value for b in RunnerBackend]),
              help="Backend to use (overrides config)")
@click.option("-t", "--timeout", type=float, help="Execution timeout")
@click.option("-w", "--workdir", type=click.Path(exists=True), help="Working directory")
@click.option("-i", "--input", "stdin_input", help="Input to send to stdin")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output")
def run_command(command, backend, timeout, workdir, stdin_input, verbose):
    """Run a command with the configured backend.

    Examples:

        sandbox run python3 -c "print('hello')"
        sandbox run -b docker python3 script.py
        sandbox run -w ./submission -t 10 python3 solution.py
    """
    settings = get_settings()

    if backend:
        settings.backend = RunnerBackend(backend)
    if timeout:
        settings.timeout = timeout
        settings.cpu_seconds = int(timeout)

    # Check backend availability
    available, message = check_backend_available(settings.backend)
    if not available:
        click.echo(click.style(f"Error: {message}", fg="red"), err=True)
        sys.exit(1)

    if verbose:
        click.echo(f"Backend: {settings.backend.value}")
        click.echo(f"Command: {' '.join(command)}")
        if workdir:
            click.echo(f"Workdir: {workdir}")
        click.echo()

    # Run
    runner = get_runner(settings)
    result = runner.run(
        list(command),
        stdin=stdin_input,
        cwd=workdir,
    )

    # Output
    if result['stdout']:
        click.echo(result['stdout'], nl=False)

    if result['stderr']:
        click.echo(click.style(result['stderr'], fg="yellow"), nl=False, err=True)

    if verbose:
        click.echo()
        if result['timed_out']:
            click.echo(click.style("Timed out!", fg="red"))
        click.echo(f"Exit code: {result['return_code']}")

    sys.exit(result['return_code'] if result['return_code'] >= 0 else 1)


@cli.command("test")
@click.option("-b", "--backend", type=click.Choice([b.value for b in RunnerBackend]),
              help="Backend to test")
def test_runner(backend):
    """Test runner functionality.

    Runs a simple test to verify the backend is working correctly.

    Examples:

        sandbox test
        sandbox test -b docker
    """
    settings = get_settings()

    if backend:
        settings.backend = RunnerBackend(backend)

    click.echo(f"Testing runner with backend: {click.style(settings.backend.value, bold=True)}\n")

    # Check availability
    available, message = check_backend_available(settings.backend)
    if not available:
        click.echo(click.style(f"✗ Backend not available: {message}", fg="red"))
        sys.exit(1)

    click.echo(click.style(f"✓ Backend available", fg="green"))

    # Test basic execution
    runner = get_runner(settings)

    tests = [
        ("Basic echo", ["echo", "hello"], "hello\n", 0),
        ("Python print", ["python3", "-c", "print('test')"], "test\n", 0),
        ("Exit code", ["python3", "-c", "exit(42)"], "", 42),
    ]

    all_passed = True
    for name, cmd, expected_stdout, expected_code in tests:
        result = runner.run(cmd)

        stdout_ok = expected_stdout in result['stdout'] or expected_stdout == ""
        code_ok = result['return_code'] == expected_code

        if stdout_ok and code_ok:
            click.echo(click.style(f"✓ {name}", fg="green"))
        else:
            click.echo(click.style(f"✗ {name}", fg="red"))
            click.echo(f"  Expected: stdout contains '{expected_stdout}', code={expected_code}")
            click.echo(f"  Got: stdout='{result['stdout'][:50]}...', code={result['return_code']}")
            all_passed = False

    click.echo()
    if all_passed:
        click.echo(click.style("All tests passed!", fg="green", bold=True))
    else:
        click.echo(click.style("Some tests failed.", fg="red"))
        sys.exit(1)


@cli.command("env")
def show_env_config():
    """Show environment variable configuration.

    Lists all environment variables that can be used to configure the runner.
    """
    click.echo("Runner Environment Variables:\n")

    vars_info = [
        ("CT_RUNNER_BACKEND", "Execution backend (local, docker)", "local"),
        ("CT_RUNNER_TIMEOUT", "Execution timeout (seconds)", "30"),
        ("CT_RUNNER_MEMORY_MB", "Memory limit (MB)", "256"),
        ("CT_RUNNER_CPU_SECONDS", "CPU time limit (seconds)", "30"),
        ("CT_RUNNER_MAX_PROCESSES", "Max processes", "10"),
        ("CT_RUNNER_NETWORK", "Enable network (1/0)", "0"),
        ("CT_RUNNER_CLEAN_ENV", "Clean environment (1/0)", "1"),
        ("CT_RUNNER_DOCKER_IMAGE", "Docker image name", "ct-sandbox:latest"),
    ]

    for var, desc, default in vars_info:
        current = click.style(f"${var}", fg="cyan")
        click.echo(f"  {current}")
        click.echo(f"    {desc}")
        click.echo(f"    Default: {default}")
        click.echo()


if __name__ == "__main__":
    cli()
