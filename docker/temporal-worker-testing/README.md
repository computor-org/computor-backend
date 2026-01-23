# Unified Testing Worker

Handles test execution for multiple programming languages:
- Python, Octave, R, Julia, C, Fortran, Document

## Architecture

### Two Python Environments

1. **Worker Environment** (Python 3.10)
   - Runs Temporal worker
   - Runs computor-testing framework CLI
   - Manages test orchestration

2. **Test Execution Environment** (Configurable, default: Python 3.13)
   - Runs actual student code
   - Has scientific/testing dependencies (numpy, scipy, matplotlib, etc.)
   - Isolated venv at `/home/worker/test-venv`

## Configuration

### Python Test Environment

Configure via environment variables in `.env` or `docker-compose-dev.yaml`:

```bash
# Python version for test execution (e.g., 3.13, 3.12, 3.11)
PYTHON_TEST_VERSION=3.13

# Additional Python packages (comma-separated)
# Example: pandas,scikit-learn,requests,beautifulsoup4
PYTHON_TEST_REQUIREMENTS=

# Computor-testing framework source
TESTING_FRAMEWORK_URL=https://gitlab.tugraz.at/.../computor-testing.git
TESTING_FRAMEWORK_TOKEN=glpat-xxxxx
TESTING_FRAMEWORK_VERSION=main
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

1. Clone/update computor-testing framework
2. Install framework in worker Python (3.10)
3. Create test execution venv (Python 3.13)
4. Install base dependencies from requirements.txt
5. Install additional configured requirements
6. Start Temporal worker

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

### Adding More Python Versions

Edit Dockerfile to install additional Python versions:
```dockerfile
RUN wget https://www.python.org/ftp/python/3.12.X/Python-3.12.X.tgz && \
    tar -xzf Python-3.12.X.tgz && \
    cd Python-3.12.X && \
    ./configure --prefix=/usr/local/python3.12 && \
    make -j$(nproc) && \
    make altinstall
```

Then set `PYTHON_TEST_VERSION=3.12` in environment.
