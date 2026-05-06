# Unified Testing Worker

Handles test execution for multiple programming languages:
- Python, Octave, R, Julia, C, Fortran, Document

## Architecture

### Two Python Environments

1. **Worker Environment** (Python 3.10)
   - Runs Temporal worker
   - Runs computor-testing framework CLI
   - Manages test orchestration

2. **Test Execution Environment** (Python 3.13, fixed at build time)
   - Runs actual student code
   - Has scientific/testing dependencies (numpy, scipy, matplotlib, etc.)
   - Isolated venv at `/home/worker/test-venv`
   - Python version is baked into the worker [Dockerfile](Dockerfile); to change
     it, edit the Dockerfile and rebuild — there is no runtime knob.

## Configuration

### Test Execution Environment

Configure via environment variable in `.env` or the docker-compose file:

```bash
# Additional Python packages installed into the test venv at worker startup
# (comma-separated). Example: pandas,scikit-learn,requests,beautifulsoup4
PYTHON_TEST_REQUIREMENTS=
```

### Base Dependencies

Automatically installed from `computor-testing/requirements.txt`:
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

**Per-Service (future enhancement):**
Configure in `deployment.yaml` service config:
```yaml
services:
  - slug: itpcp.exec.py
    config:
      python_requirements: ["pandas>=2.0", "scikit-learn"]
```
(Not yet implemented - requires dynamic package installation)

## Startup Sequence

1. Fetch service configuration from API
2. Create test execution venv (Python 3.13)
3. Install base dependencies from requirements.txt
4. Install additional configured requirements
5. Start Temporal worker

Note: computor-testing is installed at Docker build time from the monorepo.

## Development

### Building the Image

```bash
docker-compose -f docker-compose-dev.yaml build temporal-worker-testing
```

### Checking Installation

```bash
docker exec -u worker computor-fullstack-temporal-worker-testing-1 \
  /home/worker/test-venv/bin/python --version

docker exec -u worker computor-fullstack-temporal-worker-testing-1 \
  /home/worker/test-venv/bin/python -c "import numpy; print(numpy.__version__)"
```

### Changing the Test Python Version

The test Python version is hard-coded in the [Dockerfile](Dockerfile) (see the
`Python-3.13.1.tgz` download). To change it: update the URL/version in the
Dockerfile, rebuild the worker image, and rebuild the pre-built test venv.
