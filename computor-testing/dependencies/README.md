# Computor Framework - Dependency Management

A comprehensive system for managing Python, R, Octave, and system package dependencies across the Computor Framework.

## Overview

The dependency management system provides:

- **Unified configuration**: Define all dependencies in a single `dependencies.yaml` file
- **Multi-language support**: Python (pip), R (CRAN/Bioconductor/GitHub), Octave (Forge)
- **System packages**: apt packages for build dependencies
- **Docker integration**: Generate Dockerfiles from dependencies
- **Flexible installation**: Install locally or in containers
- **Validation**: Check syntax and structure of dependency files
- **Merge capability**: Combine multiple dependency files

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration File Format](#configuration-file-format)
   - [Python Dependencies](#python-dependencies)
   - [R Dependencies](#r-dependencies)
   - [Octave Dependencies](#octave-dependencies)
   - [System Dependencies](#system-dependencies)
4. [CLI Reference](#cli-reference)
5. [Docker Integration](#docker-integration)
6. [Advanced Usage](#advanced-usage)
7. [Examples](#examples)

---

## Installation

The `deps-installer` CLI is included with the Computor Framework:

```bash
# Install the framework (includes deps-installer)
cd computor-testing
pip install -e .

# Verify installation
deps-installer --version
deps-installer --help
```

---

## Quick Start

### 1. Create a dependencies.yaml file

```yaml
python:
  version: ">=3.10"
  packages:
    - numpy
    - pandas
    - matplotlib

r:
  packages:
    - jsonlite
    - ggplot2

octave:
  packages:
    - signal
    - statistics
```

### 2. Validate the file

```bash
deps-installer validate -f dependencies.yaml
```

### 3. Install dependencies

```bash
# Install everything
deps-installer install -f dependencies.yaml

# Dry-run (show commands without executing)
deps-installer install -f dependencies.yaml --dry-run

# Install only Python packages
deps-installer install -f dependencies.yaml --no-r --no-octave --no-system
```

---

## Configuration File Format

The `dependencies.yaml` file has four main sections: `python`, `r`, `octave`, and `system`.

### Python Dependencies

```yaml
python:
  # Minimum Python version required
  version: ">=3.10"

  # Package manager (currently only pip supported)
  manager: pip

  # Package list
  packages:
    # Simple package (latest version)
    - numpy

    # Package with version constraint
    - name: scipy
      version: ">=1.9"

    # Package with exact version
    - name: pandas
      version: "==2.0.0"

    # Package with multiple constraints
    - name: matplotlib
      version: ">=3.5,<4.0"

    # Package with extras
    - name: requests
      extras:
        - security
        - socks

    # Package from git repository
    - name: my-package
      git: https://github.com/user/repo.git
      branch: main  # or tag, commit

    # Package from URL
    - name: custom-pkg
      url: https://example.com/package.whl
```

#### Version Specifiers

| Specifier | Meaning |
|-----------|---------|
| `>=1.0` | Version 1.0 or higher |
| `<=2.0` | Version 2.0 or lower |
| `==1.5.0` | Exactly version 1.5.0 |
| `!=1.3` | Any version except 1.3 |
| `~=1.4` | Compatible release (>=1.4, <2.0) |
| `>=1.0,<2.0` | Range (1.0 to 2.0) |

### R Dependencies

```yaml
r:
  # Minimum R version required
  version: ">=4.0"

  # CRAN mirror URL
  cran_mirror: "https://cloud.r-project.org/"

  # Local library path for installation
  lib_path: "~/.local/lib/R"

  # Package list
  packages:
    # Simple CRAN package
    - jsonlite

    # CRAN package with version
    - name: dplyr
      version: ">=1.0"

    # Package from GitHub
    - name: devtools
      github: r-lib/devtools
      ref: main  # branch, tag, or commit

    # Bioconductor package
    - name: Biostrings
      bioconductor: true

    # Package from URL
    - name: custom-pkg
      url: https://example.com/package.tar.gz
```

#### R Package Sources

| Source | Field | Example |
|--------|-------|---------|
| CRAN | (default) | `- ggplot2` |
| GitHub | `github` | `github: tidyverse/ggplot2` |
| Bioconductor | `bioconductor: true` | `bioconductor: true` |
| URL | `url` | `url: https://...` |

### Octave Dependencies

```yaml
octave:
  # Minimum Octave version required
  version: ">=6.0"

  # Use Octave Forge (default: true)
  forge: true

  # Package list
  packages:
    # Forge package (simple)
    - signal

    # Forge package with version
    - name: statistics
      version: ">=1.4"

    # Package from URL
    - name: custom-pkg
      url: https://example.com/package.tar.gz
      forge: false
```

#### Octave Package Sources

| Source | Description |
|--------|-------------|
| Forge | Default. Uses `pkg install -forge name` |
| URL | Custom package URL. Uses `pkg install "url"` |

### System Dependencies

```yaml
system:
  # APT packages (Debian/Ubuntu)
  apt:
    # Build essentials
    - build-essential
    - gcc
    - g++

    # Development libraries
    - libcurl4-openssl-dev
    - libssl-dev
    - libxml2-dev

    # For plotting/graphics
    - libfontconfig1-dev
    - libfreetype6-dev
    - libpng-dev

    # Other tools
    - git
    - curl
    - wget

  # Environment variables to set
  env:
    LC_ALL: C.UTF-8
    LANG: C.UTF-8
```

---

## CLI Reference

### `deps-installer validate`

Validate a dependencies.yaml file.

```bash
deps-installer validate -f dependencies.yaml
```

**Options:**
- `-f, --file PATH`: Path to dependencies.yaml (default: `dependencies.yaml`)

**Output:**
```
✓ dependencies.yaml is valid
  Python packages: 6
  R packages: 4
  Octave packages: 4
  System packages (apt): 9
```

### `deps-installer install`

Install dependencies from a dependencies.yaml file.

```bash
# Install all
deps-installer install -f dependencies.yaml

# Dry run
deps-installer install -f dependencies.yaml --dry-run

# Selective installation
deps-installer install -f dependencies.yaml --no-python
deps-installer install -f dependencies.yaml --no-r
deps-installer install -f dependencies.yaml --no-octave
deps-installer install -f dependencies.yaml --no-system

# Custom R library path
deps-installer install -f dependencies.yaml --r-lib-path ~/.local/lib/R
```

**Options:**
- `-f, --file PATH`: Path to dependencies.yaml
- `--python/--no-python`: Install Python packages (default: yes)
- `--r/--no-r`: Install R packages (default: yes)
- `--octave/--no-octave`: Install Octave packages (default: yes)
- `--system/--no-system`: Install system packages (default: yes)
- `--dry-run`: Show commands without executing
- `--r-lib-path PATH`: Override R library path

### `deps-installer export`

Export dependencies in various formats.

```bash
# Python requirements.txt format
deps-installer export -f dependencies.yaml -F pip

# R installation script
deps-installer export -f dependencies.yaml -F r

# Octave installation script
deps-installer export -f dependencies.yaml -F octave

# APT package list
deps-installer export -f dependencies.yaml -F apt
```

**Options:**
- `-f, --file PATH`: Path to dependencies.yaml
- `-F, --format FORMAT`: Output format (`pip`, `r`, `octave`, `apt`)

**Example Output (pip):**
```
# Python >=3.10

numpy
scipy>=1.9
matplotlib>=3.5
pandas
sympy
uncertainties
```

**Example Output (r):**
```r
# R >=4.0
options(repos = c(CRAN = 'https://cloud.r-project.org/'))

dir.create('~/.local/lib/R', recursive = TRUE, showWarnings = FALSE)

install.packages(c('jsonlite', 'dplyr', 'tidyr', 'ggplot2'), lib = '~/.local/lib/R')
```

### `deps-installer dockerfile`

Generate a Dockerfile from dependencies.

```bash
# Basic (Python only)
deps-installer dockerfile -f dependencies.yaml

# With R support
deps-installer dockerfile -f dependencies.yaml --include-r

# With Octave support
deps-installer dockerfile -f dependencies.yaml --include-octave

# Full (Python + R + Octave)
deps-installer dockerfile -f dependencies.yaml --include-r --include-octave

# Custom base image
deps-installer dockerfile -f dependencies.yaml --base-image python:3.11-slim

# Write to file
deps-installer dockerfile -f dependencies.yaml -o Dockerfile
```

**Options:**
- `-f, --file PATH`: Path to dependencies.yaml
- `-o, --output PATH`: Output file (default: stdout)
- `--base-image IMAGE`: Base Docker image (default: `ubuntu:22.04`)
- `--python-version VERSION`: Python version (default: `3.11`)
- `--include-r`: Include R installation
- `--include-octave`: Include Octave installation

### `deps-installer merge`

Merge multiple dependency files into one.

```bash
deps-installer merge file1.yaml file2.yaml file3.yaml -o merged.yaml
```

**Options:**
- `FILES`: One or more dependency files to merge
- `-o, --output PATH`: Output file (default: `merged-dependencies.yaml`)

**Merge Behavior:**
- Package lists are combined (duplicates removed)
- Version constraints use the most restrictive
- Settings from later files override earlier ones

---

## Docker Integration

### Generate a Complete Dockerfile

```bash
deps-installer dockerfile -f dependencies.yaml --include-r --include-octave -o Dockerfile
```

**Generated Dockerfile:**

```dockerfile
# Auto-generated from dependencies.yaml
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    r-base \
    r-base-dev \
    octave \
    build-essential \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip3 install --no-cache-dir \
    'numpy' \
    'scipy>=1.9' \
    'matplotlib>=3.5'

# R dependencies
RUN Rscript -e "install.packages(c('jsonlite', 'ggplot2'), repos='https://cloud.r-project.org/')"

# Octave dependencies
RUN octave --eval "pkg install -forge signal"
RUN octave --eval "pkg install -forge statistics"

# Set working directory
WORKDIR /app
```

### Multi-Stage Build Example

For production use, consider a multi-stage build:

```dockerfile
# Build stage
FROM ubuntu:22.04 AS builder

# ... install build dependencies ...

# Runtime stage
FROM ubuntu:22.04

# Copy only runtime dependencies
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
```

---

## Advanced Usage

### Environment-Specific Dependencies

Create separate files for different environments:

```
dependencies/
├── base.yaml           # Core packages
├── dev.yaml            # Development tools
├── test.yaml           # Testing packages
└── production.yaml     # Production-only
```

Merge them for deployment:

```bash
# Development environment
deps-installer merge dependencies/base.yaml dependencies/dev.yaml -o dev-deps.yaml

# Production environment
deps-installer merge dependencies/base.yaml dependencies/production.yaml -o prod-deps.yaml
```

### CI/CD Integration

**GitHub Actions Example:**

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps-installer
        run: pip install ./computor-testing

      - name: Validate dependencies
        run: deps-installer validate -f dependencies.yaml

      - name: Install dependencies
        run: deps-installer install -f dependencies.yaml --no-system
```

### Extracting Dependencies from Examples

To collect all unique packages from multiple meta.yaml files:

```bash
# Find all Python imports used
grep -rh "^import\|^from" itpcp.progphys.py/ | sort -u

# Extract from meta.yaml files
for f in itpcp.progphys.py/*/meta.yaml; do
  echo "=== $f ==="
  grep -A5 "testDependencies:" "$f"
done
```

---

## Examples

### Minimal Python Project

```yaml
python:
  packages:
    - numpy
    - pytest
```

### Data Science Stack

```yaml
python:
  version: ">=3.10"
  packages:
    - numpy
    - pandas
    - scipy
    - matplotlib
    - seaborn
    - scikit-learn
    - jupyter

system:
  apt:
    - libopenblas-dev
    - liblapack-dev
```

### Scientific Computing (Python + R)

```yaml
python:
  version: ">=3.10"
  packages:
    - numpy
    - scipy
    - matplotlib
    - sympy

r:
  version: ">=4.0"
  packages:
    - jsonlite
    - ggplot2
    - dplyr
    - tidyr

system:
  apt:
    - build-essential
    - libcurl4-openssl-dev
    - libssl-dev
```

### Signal Processing (Octave)

```yaml
octave:
  version: ">=6.0"
  forge: true
  packages:
    - signal
    - control
    - communications
    - image

system:
  apt:
    - octave
    - liboctave-dev
    - gnuplot
```

### Full Computor Framework

```yaml
python:
  version: ">=3.10"
  packages:
    - numpy
    - scipy
    - matplotlib
    - pandas
    - sympy
    - uncertainties
    - pydantic
    - click
    - pyyaml

r:
  version: ">=4.0"
  cran_mirror: "https://cloud.r-project.org/"
  lib_path: "~/.local/lib/R"
  packages:
    - jsonlite
    - testthat
    - dplyr
    - ggplot2

octave:
  version: ">=6.0"
  forge: true
  packages:
    - signal
    - statistics
    - optim
    - control

system:
  apt:
    - build-essential
    - gcc
    - g++
    - libcurl4-openssl-dev
    - libssl-dev
    - libxml2-dev
    - libfontconfig1-dev
    - libfreetype6-dev
    - libpng-dev
    - octave
    - r-base
    - r-base-dev
```

---

## Troubleshooting

### Common Issues

**1. R packages fail to install**

Ensure system dependencies are installed first:
```bash
sudo apt-get install libcurl4-openssl-dev libssl-dev libxml2-dev
```

**2. Octave Forge packages fail**

Check Octave version and network connectivity:
```bash
octave --version
octave --eval "pkg list"
```

**3. Python packages have conflicts**

Use `pip check` to identify conflicts:
```bash
pip check
```

**4. Permission denied for R library**

Create the library directory with proper permissions:
```bash
mkdir -p ~/.local/lib/R
R_LIBS_USER=~/.local/lib/R Rscript -e "install.packages('jsonlite')"
```

### Debug Mode

For verbose output during installation:

```bash
# Show all commands (dry-run)
deps-installer install -f dependencies.yaml --dry-run

# Check what would be installed
deps-installer export -f dependencies.yaml -F pip
deps-installer export -f dependencies.yaml -F r
deps-installer export -f dependencies.yaml -F octave
```

---

## API Reference

For programmatic use, import the models directly:

```python
from dependencies import Dependencies, PythonDependencies, RDependencies

# Load from file
deps = Dependencies.from_yaml("dependencies.yaml")

# Access components
print(deps.python.to_pip_list())
print(deps.r.to_install_script())
print(deps.octave.to_install_script())

# Generate requirements.txt
print(deps.python.to_requirements_txt())

# Merge dependencies
deps1 = Dependencies.from_yaml("file1.yaml")
deps2 = Dependencies.from_yaml("file2.yaml")
merged = deps1.merge(deps2)

# Export to YAML
print(merged.to_yaml())
```

---

## Contributing

When adding new features to the dependency system:

1. Update `models.py` with new Pydantic models
2. Update `installer.py` with new CLI commands
3. Update `schema.yaml` with documentation
4. Update this README with examples
5. Add tests for new functionality

---

## License

Part of the Computor Framework. See the main project LICENSE file.
