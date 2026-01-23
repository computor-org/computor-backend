#!/usr/bin/env python3
"""
Unified Testing Worker Startup Script

This script:
1. Clones/updates the computor-testing repository from GitLab
2. Installs the computor-testing framework
3. Starts the Temporal worker for unified multi-language testing

Supports: Python, Octave, R, Julia, C/C++, Fortran, Document analysis
"""

import os
import sys
import subprocess
from computor_types.repositories import Repository


def main():
    print("=" * 80)
    print("Starting Unified Testing Worker")
    print("=" * 80)

    # Get environment configuration
    TESTING_FRAMEWORK_URL = os.getenv("TESTING_FRAMEWORK_URL")
    TESTING_FRAMEWORK_TOKEN = os.getenv("TESTING_FRAMEWORK_TOKEN")
    TESTING_FRAMEWORK_VERSION = os.getenv("TESTING_FRAMEWORK_VERSION") or "main"

    if not TESTING_FRAMEWORK_URL:
        print("WARNING: TESTING_FRAMEWORK_URL not set, using default")
        TESTING_FRAMEWORK_URL = "https://gitlab.tugraz.at/codeability/testing-frameworks/computor-testing"

    if TESTING_FRAMEWORK_TOKEN is None:
        print("WARNING: No TESTING_FRAMEWORK_TOKEN available.")
        print("         Public repository access only.")

    framework_repo_path = os.path.abspath("/home/worker/computor-testing")
    # The actual package is in a subdirectory (monorepo structure)
    framework_package_path = os.path.join(framework_repo_path, "computor-testing")

    # Step 1: Clone or update computor-testing repository
    print("\n[1/3] Fetching computor-testing framework...")
    print(f"  URL: {TESTING_FRAMEWORK_URL}")
    print(f"  Version: {TESTING_FRAMEWORK_VERSION}")
    print(f"  Target: {framework_repo_path}")

    try:
        result = Repository(
            url=TESTING_FRAMEWORK_URL,
            token=TESTING_FRAMEWORK_TOKEN,
            branch=TESTING_FRAMEWORK_VERSION
        ).clone_or_fetch(framework_repo_path)
        print(f"  ✓ {result}")
    except Exception as e:
        print(f"  ✗ FAILED: git clone/fetch failed [{str(e)}]")
        print("\nContinuing without computor-testing framework...")
        print("Worker will only support legacy testing backends.")

    # Step 2: Install computor-testing framework AND create test execution venv
    if os.path.exists(framework_package_path) and os.path.exists(os.path.join(framework_package_path, "pyproject.toml")):
        print("\n[2/3] Installing computor-testing framework...")
        print(f"  Package path: {framework_package_path}")

        # 2a: Install computor-testing framework in worker Python (3.10)
        cmd = f"pip install --user {framework_package_path}"
        print(f"  Command: {cmd}")
        result = subprocess.run(cmd, cwd=framework_package_path, shell=True)

        if result.returncode == 0:
            print("\n  ✓ computor-testing installed successfully (worker environment)")

            # Verify installation
            verify_cmd = "computor-test --version"
            verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if verify_result.returncode == 0:
                print(f"  ✓ computor-test CLI available: {verify_result.stdout.strip()}")
            else:
                print("  ⚠ computor-test CLI not found in PATH")
        else:
            print(f"\n  ✗ Installation failed (exit code: {result.returncode})")
            print("\nContinuing without computor-testing framework...")

        # 2b: Create Python test execution environment (configurable version and dependencies)
        print("\n  Creating Python test execution environment...")

        # Get configuration from environment variables (passed from docker-compose or deployment)
        python_version = os.getenv("PYTHON_TEST_VERSION", "3.13")
        test_requirements = os.getenv("PYTHON_TEST_REQUIREMENTS", "")  # Comma-separated package list
        test_venv_path = "/home/worker/test-venv"

        print(f"  Python version: {python_version}")
        print(f"  Additional requirements: {test_requirements if test_requirements else '(none)'}")

        # Create venv with specified Python version
        python_executable = f"python{python_version}"
        venv_create = subprocess.run(
            f"{python_executable} -m venv {test_venv_path}",
            shell=True,
            capture_output=True,
            text=True
        )

        if venv_create.returncode == 0:
            print(f"  ✓ Created venv at {test_venv_path} (Python {python_version})")

            # Install base testing dependencies from computor-testing requirements.txt
            print("  Installing base test dependencies (numpy, scipy, matplotlib, etc.)...")
            requirements_path = os.path.join(framework_package_path, "requirements.txt")
            if os.path.exists(requirements_path):
                pip_install = subprocess.run(
                    f"{test_venv_path}/bin/pip install -r {requirements_path}",
                    shell=True
                )

                if pip_install.returncode == 0:
                    print("  ✓ Base dependencies installed")
                else:
                    print(f"  ⚠ Failed to install base dependencies")
            else:
                print(f"  ⚠ requirements.txt not found, skipping base dependencies")

            # Install additional requirements if specified
            if test_requirements:
                print(f"  Installing additional requirements: {test_requirements}")
                # Split by comma and install each package
                packages = [pkg.strip() for pkg in test_requirements.split(",") if pkg.strip()]
                if packages:
                    pip_install_extra = subprocess.run(
                        f"{test_venv_path}/bin/pip install {' '.join(packages)}",
                        shell=True
                    )
                    if pip_install_extra.returncode == 0:
                        print(f"  ✓ Additional requirements installed")
                    else:
                        print(f"  ⚠ Failed to install some additional requirements")

            # Verify numpy in test venv
            numpy_check = subprocess.run(
                f"{test_venv_path}/bin/python -c 'import numpy; print(numpy.__version__)'",
                shell=True,
                capture_output=True,
                text=True
            )
            if numpy_check.returncode == 0:
                print(f"  ✓ numpy available in test venv: {numpy_check.stdout.strip()}")

            # Verify Python version in test venv
            version_check = subprocess.run(
                f"{test_venv_path}/bin/python --version",
                shell=True,
                capture_output=True,
                text=True
            )
            if version_check.returncode == 0:
                print(f"  ✓ Test venv Python: {version_check.stdout.strip()}")

            # Set environment variable for PyExecutor to use test venv Python
            os.environ["PYTHON_TEST_EXECUTABLE"] = f"{test_venv_path}/bin/python"
            print(f"  ✓ Set PYTHON_TEST_EXECUTABLE={test_venv_path}/bin/python")
        else:
            print(f"  ⚠ Failed to create test venv: {venv_create.stderr}")
            print(f"  Tests will run in worker Python (3.10) instead")
    else:
        print("\n[2/3] Skipping computor-testing installation (not available)")
        print(f"  Checked path: {framework_package_path}")
        print(f"  Path exists: {os.path.exists(framework_package_path)}")
        if os.path.exists(framework_package_path):
            print(f"  Contents: {os.listdir(framework_package_path)}")

    # Step 3: Start Temporal worker
    print("\n[3/3] Starting Temporal worker...")

    # Pass command line arguments to the temporal worker
    # This allows docker-compose to specify --queues=testing
    args = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    cmd = f"python -m computor_backend.tasks.temporal_worker {args}"
    print(f"  Command: {cmd}")

    print("\n" + "=" * 80)
    print("Worker Starting - Logs will follow")
    print("=" * 80 + "\n")

    # Use Popen to allow logs to flow through
    # Forward stdout/stderr so we can see worker activity in Docker logs
    subprocess.Popen(
        cmd,
        cwd=os.path.abspath(os.path.expanduser("~")),
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    ).wait()  # Wait for worker to finish (blocks forever)


if __name__ == '__main__':
    main()
