# Unified Testing Worker

Handles test execution for multiple programming languages:
- Python, Octave, R, Julia, C, Fortran, Document

## Architecture

### Two Python Environments

1. **Worker Environment** (Python 3.12)
   - Runs Temporal worker
   - Runs computor-testing framework CLI
   - Manages test orchestration

2. **Test Execution Environment** (Python 3.13, fixed at build time)
   - Runs actual student code
   - Has scientific/testing dependencies (numpy, scipy, matplotlib, etc.)
   - Isolated venv at `/home/worker/test-venv`
   - Python version is baked into the
     [testing-runtimes Dockerfile](../testing-runtimes/Dockerfile); to change it,
     edit that Dockerfile and rebuild — there is no runtime knob.

## Configuration

### Test Execution Environment

Configure via environment variable in `.env` or the docker-compose file:

```bash
# Additional Python packages installed into the test venv at worker startup
# (comma-separated). Example: pandas,scikit-learn,requests,beautifulsoup4
PYTHON_TEST_REQUIREMENTS=
```

### Base Dependencies

Installed at image build time from the hashed `computor-testing/requirements.lock`
(compiled from `computor-testing/requirements.txt`), including:
- numpy
- scipy
- matplotlib
- pytest
- pydantic
- PyYAML

### Adding Custom Dependencies

**Global (all tests):**
```bash
# In .env
PYTHON_TEST_REQUIREMENTS=pandas,scikit-learn,requests
```

## Startup Sequence

1. Fetch service configuration from API (`GET /service-accounts/me`)
2. Verify the pre-built test venv (Python 3.13 with the base dependencies;
   recreated only if missing)
3. Install additional configured requirements (`PYTHON_TEST_REQUIREMENTS`)
4. Start Temporal worker

Note: computor-testing and the test venv are installed at Docker build time from the monorepo.

## Development

### Building the Image

```bash
./computor.sh up dev --build -d
```

### Checking Installation

```bash
docker exec -u worker computor-temporal-worker-testing-1 \
  /home/worker/test-venv/bin/python --version

docker exec -u worker computor-temporal-worker-testing-1 \
  /home/worker/test-venv/bin/python -c "import numpy; print(numpy.__version__)"
```

### Changing the Test Python Version

The test Python version is pinned in the
[testing-runtimes Dockerfile](../testing-runtimes/Dockerfile)
(`PYTHON313_VERSION` and `PYTHON313_SHA256`). To change it, update both and
rebuild with `./computor.sh up dev --build --build-base=testing-runtimes -d`.
