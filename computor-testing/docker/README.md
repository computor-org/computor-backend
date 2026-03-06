# Docker Images for Computor Testing Framework

This directory contains example Dockerfiles for running each language tester in a secure, isolated container.

## Available Images

| Dockerfile | Language | Tester Command | Description |
|------------|----------|----------------|-------------|
| `Dockerfile.python` | Python | `pytester` | Python 3.12 with numpy, scipy, pandas, matplotlib |
| `Dockerfile.octave` | Octave/MATLAB | `octester` | GNU Octave with common toolboxes |
| `Dockerfile.r` | R | `rtester` | R with tidyverse, ggplot2 |
| `Dockerfile.julia` | Julia | `jltester` | Julia 1.10 with common packages |
| `Dockerfile.c` | C/C++ | `ctester` | GCC/G++ with cmake, valgrind |
| `Dockerfile.fortran` | Fortran | `ftester` | GFortran with BLAS/LAPACK |
| `Dockerfile.document` | Documents | `doctester` | Minimal image for text analysis |
| `Dockerfile.full` | All | All testers | Full image with all languages |

## Building Images

Build from the project root directory (parent of `computor-testing`):

```bash
# Single language
docker build -f docker/Dockerfile.python -t ct-python .
docker build -f docker/Dockerfile.octave -t ct-octave .
docker build -f docker/Dockerfile.r -t ct-r .

# Full image (all languages)
docker build -f docker/Dockerfile.full -t ct-full .
```

## Running Tests

All images use the same security options for isolation:

```bash
docker run --rm \
  --user 1000:1000 \
  --read-only \
  --tmpfs /tmp:size=100M,mode=1777 \
  --tmpfs /sandbox:size=50M,mode=1777 \
  --network none \
  --memory 512m \
  --cpus 1 \
  --pids-limit 100 \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  -v /path/to/submission:/sandbox/submission:ro \
  -v /path/to/tests:/sandbox/tests:ro \
  -v /path/to/output:/sandbox/output:rw \
  ct-python \
  pytester run -t /sandbox/submission -T /sandbox/tests/test.yaml
```

## Security Features

All images implement:

- **Non-root user**: Runs as uid 1000
- **Read-only filesystem**: Only `/tmp` and `/sandbox` are writable
- **Network isolation**: `--network none` prevents network access
- **Resource limits**: Memory, CPU, and process limits
- **Capability dropping**: All Linux capabilities dropped
- **No privilege escalation**: `no-new-privileges` seccomp option

## Customization

These are example images. For production use, consider:

1. **Pinning versions**: Use specific package versions for reproducibility
2. **Multi-stage builds**: Reduce image size by separating build and runtime
3. **Custom packages**: Add course-specific libraries as needed
4. **Caching**: Use Docker layer caching for faster builds

## Directory Structure

When running a container, mount directories as:

```
/sandbox/
├── submission/  (ro) - Student code to test
├── tests/       (ro) - Test configuration (test.yaml, reference/)
└── output/      (rw) - Test results (report.json)
```
