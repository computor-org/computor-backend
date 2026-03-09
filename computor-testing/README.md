# Computor Testing Framework

A pytest-based testing framework for evaluating code submissions in multiple languages, designed for educational use at TU Graz.

## Supported Languages

| Language | Command | Test Types |
|----------|---------|------------|
| Python | `computor-test python run` | variable, structural |
| Octave/MATLAB | `computor-test octave run` | variable, graphics, structural |
| R | `computor-test r run` | variable, structural |
| Julia | `computor-test julia run` | variable, structural |
| C/C++ | `computor-test c run` | stdout, exitcode, compile |
| Fortran | `computor-test fortran run` | stdout, exitcode, compile |
| Document/Text | `computor-test document run` | wordcount, linecount, keyword, section |

## Features

- **Variable Testing**: Compare student variables against reference values with configurable tolerances
- **stdout Testing**: Compare program output for compiled languages (C, Fortran)
- **Graphics Testing**: Verify graphical output properties (axes, labels, data)
- **Structural Testing**: Check for specific keywords/constructs in code
- **Document Testing**: Analyze text files for word count, structure, keywords, and more
- **Existence Tests**: Verify required files exist
- **Token Exchange**: Dynamic file/command substitution in test code
- **Success Dependencies**: Chain tests based on previous results
- **Path Security**: Validation against directory traversal attacks

## Installation

```bash
# Install from directory
pip install /path/to/computor-testing

# Or for development (editable mode)
pip install -e /path/to/computor-testing
```

## Requirements

- Python >= 3.10
- Language-specific requirements:
  - **Octave**: GNU Octave in PATH
  - **R**: R with jsonlite package
  - **Julia**: Julia with JSON package
  - **C/C++**: gcc/g++ compiler
  - **Fortran**: gfortran compiler
  - **Document**: No additional requirements

### R Setup

```bash
mkdir -p ~/.local/lib/R/library
Rscript -e "install.packages('jsonlite', repos='https://cloud.r-project.org/', lib='~/.local/lib/R/library')"
export R_LIBS_USER=~/.local/lib/R/library
```

### Julia Setup

```bash
julia -e 'import Pkg; Pkg.add("JSON")'
```

## Usage

### Unified CLI

The `computor-test` command provides a unified interface for all language testers:

```bash
# List available testers and their status
computor-test list

# Check all language runtimes
computor-test check --all

# Check a specific runtime
computor-test check python
```

### Running Tests

```bash
# Python
computor-test python run -t ./student -T test.yaml

# Octave
computor-test octave run -t ./student -T test.yaml

# R
R_LIBS_USER=~/.local/lib/R/library computor-test r run -t ./student -T test.yaml

# Julia
computor-test julia run -t ./student -T test.yaml

# C/C++
computor-test c run -t ./student -T test.yaml

# Fortran
computor-test fortran run -t ./student -T test.yaml

# Document
computor-test document run -t ./student -T test.yaml
```

### Legacy Commands

For backward compatibility, individual tester commands are still available:

```bash
pytester run -t ./student -T test.yaml
octester run -t ./student -T test.yaml
rtester run -t ./student -T test.yaml
jltester run -t ./student -T test.yaml
ctester run -t ./student -T test.yaml
ftester run -t ./student -T test.yaml
doctester run -t ./student -T test.yaml
```

### Check Installation

```bash
# Unified
computor-test check --all

# Or individual
computor-test python check
computor-test octave check
```

## Test YAML Format

```yaml
name: Simple Computations
description: Basic arithmetic tests
type: octave
version: "1.0"

properties:
  relativeTolerance: 1e-12
  absoluteTolerance: 0.0001
  tests:
    - type: exist
      name: Check file exists
      tests:
        - name: script.m

    - type: variable
      name: Basic variables
      entryPoint: script.m
      tests:
        - name: result
          value: 42

    - type: structural
      name: No loops allowed
      file: script.m
      tests:
        - name: no_for
          pattern: "\\bfor\\b"
          allowedOccuranceRange: [0, 0]
```

### stdout Testing (C, Fortran)

```yaml
name: Hello World
type: c
version: "1.0"

properties:
  tests:
    - type: stdout
      name: Output tests
      entryPoint: main.c
      tests:
        - name: greeting
          qualification: contains
          value: "Hello"

        - name: exact_match
          qualification: matches
          value: "Hello, World!\n"

        - name: pattern
          qualification: regexp
          value: "Result: \\d+"
```

### File Existence Testing (All Languages)

The `exist` test type is available across ALL language testers:

```yaml
properties:
  tests:
    - type: exist
      name: Required Files
      tests:
        - name: solution.py      # Exact filename
        - name: data/*.csv       # Glob pattern
        - name: output/result.json  # Path with directory
        - name: config.json
          allowEmpty: true       # Allow empty files (default: false)
```

### Document Testing

```yaml
name: Essay Requirements
type: document
version: "1.0"

properties:
  tests:
    - type: exist
      name: File Check
      tests:
        - name: essay.md

    - type: wordcount
      name: Word Count
      file: essay.md
      tests:
        - name: minimum_words
          allowedOccuranceRange: [500, 0]

    - type: section
      name: Required Sections
      file: essay.md
      tests:
        - name: Introduction
        - name: Methodology
        - name: Conclusion

    - type: keyword
      name: Keywords
      file: essay.md
      tests:
        - name: algorithm
          allowedOccuranceRange: [3, 0]
```

## Test Types

| Type | Languages | Description |
|------|-----------|-------------|
| `variable` | Octave, Python, R, Julia | Compare workspace variables |
| `stdout` | C, Fortran | Compare program output |
| `graphics` | Octave | Check graphical properties |
| `structural` | All | Count keyword/pattern occurrences |
| `exist` | All | File existence check |
| `error` | Interpreted | Error handling tests |
| `warning` | Interpreted | Warning tests |
| `wordcount` | Document | Check word count |
| `linecount` | Document | Check line count |
| `charcount` | Document | Check character count |
| `paragraphcount` | Document | Check paragraph count |
| `sentencecount` | Document | Check sentence count |
| `headingcount` | Document | Check markdown heading count |
| `section` | Document | Check for required sections |
| `keyword` | Document | Check keyword presence/frequency |
| `pattern` | Document | Regex pattern matching |
| `uniquewords` | Document | Check vocabulary size |
| `linkcount` | Document | Check markdown link count |
| `imagecount` | Document | Check markdown image count |
| `codeblockcount` | Document | Check code block count |
| `listitemcount` | Document | Check list item count |

### stdout Qualifications

| Qualification | Description |
|---------------|-------------|
| `matches` | Exact string match |
| `contains` | Substring present |
| `startsWith` | Output begins with value |
| `endsWith` | Output ends with value |
| `regexp` | Regular expression match |
| `exitCode` | Check program return value |

## Project Structure

```
computor-testing/
├── ctcore/           # Computor Testing Core
│   ├── models.py     # Pydantic models (TestSuite, Specification, Report)
│   ├── helpers.py    # Utility functions
│   ├── security.py   # Path validation
│   └── stdio.py      # stdout comparison utilities
├── ctexec/           # Computor Testing Execution
│   ├── base.py       # BaseExecutor abstract class
│   ├── interpreted.py # InterpretedExecutor (Python, R, Julia, Octave)
│   ├── compiled.py   # CompiledExecutor (C, Fortran)
│   └── environment.py # Safe environment handling
├── testers/          # Unified testers package
│   ├── cli.py        # Unified CLI (computor-test)
│   ├── base.py       # BaseTester class
│   ├── executors/    # Language-specific executors
│   │   ├── python.py
│   │   ├── octave.py
│   │   ├── r.py
│   │   ├── julia.py
│   │   ├── c.py
│   │   ├── fortran.py
│   │   └── document.py
│   ├── runners/      # Language-specific test runners
│   │   └── ...
│   └── tests/        # pytest test classes per language
│       ├── python/
│       ├── octave/
│       ├── r/
│       ├── julia/
│       ├── c/
│       ├── fortran/
│       └── document/
├── sandbox/          # Execution backends
│   ├── config.py     # RunnerBackend, RunnerSettings
│   ├── backends.py   # LocalRunner, DockerRunner
│   └── cli.py        # sandbox CLI
├── blocks/           # Test YAML generation tools
├── dependencies/     # Package management
└── pyproject.toml    # Package configuration
```

## Execution Backends

Configure execution via environment variables:

```bash
# Use local execution (default)
export CT_RUNNER_BACKEND=local

# Use Docker for isolation
export CT_RUNNER_BACKEND=docker
export CT_RUNNER_DOCKER_IMAGE=ct-sandbox:latest

# Resource limits
export CT_RUNNER_TIMEOUT=30
export CT_RUNNER_MEMORY_MB=256
```

Check available backends:

```bash
sandbox check
sandbox test
```

## meta.yaml Configuration

The `meta.yaml` file configures exercise metadata and execution settings:

```yaml
identifier: itpcp.pgph.c.hello_world
version: '1.0'
title: Hello World in C
description: A simple Hello World program
license: CC BY-NC 4.0

authors:
  - name: ITP Team
    email: itp@tugraz.at
    affiliation: TU Graz

properties:
  studentSubmissionFiles:
    - hello.c
  executionBackend:
    slug: itpcp.exec.c
    version: "13"
    settings:
      timeout: 60
      compileTimeout: 30
      memoryLimitMB: 256
      compiler: gcc
      flags: ["-Wall", "-Wextra"]
```

### ExecutionBackend Settings

| Setting | Type | Description |
|---------|------|-------------|
| `timeout` | float | Execution timeout in seconds |
| `compileTimeout` | float | Compilation timeout (compiled languages) |
| `memoryLimitMB` | int | Memory limit in megabytes |
| `cpuLimit` | int | CPU time limit in seconds |
| `maxProcesses` | int | Maximum processes/threads |
| `env` | list | Environment variables (`KEY=VALUE`) |
| `compiler` | string | Compiler to use (gcc, g++, gfortran) |
| `flags` | list | Compiler/interpreter flags |

**Priority:** `test.yaml` > `meta.yaml` > tester defaults

## Assignment Directory Structure

```
assignment/
├── test.yaml              # Test definitions
├── meta.yaml              # Metadata (optional)
├── reference/             # Reference solution
│   └── solution.m
├── localTests/
│   ├── correctSolution/   # Should pass all tests
│   └── wrongSolution/     # Should fail some tests
└── output/
    └── testSummary.json   # Test results
```

## Output Format

Tests produce `testSummary.json`:

```json
{
  "timestamp": "2024-12-03T10:30:00.000000+00:00",
  "type": "julia",
  "duration": 15.72,
  "environment": {
    "julia_version": "1.10.0"
  },
  "resultMessage": "30/30 tests passed",
  "tests": [
    {
      "name": "result",
      "result": "PASSED",
      "message": "Variable matches expected value"
    }
  ]
}
```

## Additional CLI Tools

### Blocks CLI (test.yaml Generation)

The `blocks` CLI generates test.yaml files and exports block definitions for the VSCode extension:

```bash
# Initialize a new test.yaml
blocks init -l python -n "My Tests"

# Generate test snippets
blocks generate -l python -t variable -n result

# Browse and use templates
blocks templates list
blocks templates show "Variable Check" -l python

# Export for VSCode extension integration
blocks export ./generated
```

See [blocks/README.md](blocks/README.md) for full documentation.

### Dependency Installer

The `deps-installer` CLI manages exercise dependencies across languages:

```bash
# Install dependencies from dependencies.yaml
deps-installer install -f dependencies.yaml

# Generate Dockerfile from dependencies
deps-installer dockerfile -f dependencies.yaml -o Dockerfile

# Validate dependencies file
deps-installer validate -f dependencies.yaml
```

See [dependencies/README.md](dependencies/README.md) for full documentation.

## Documentation

- [User Guide](docs/USER_GUIDE.md) - For exercise authors writing test.yaml files
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - For developers extending the framework
- [Audit Report](docs/AUDIT_REPORT.md) - Code quality findings and recommendations
- [Blocks README](blocks/README.md) - Block system for VSCode extension
- [Dependencies README](dependencies/README.md) - Dependency management
- [Security Policy](SECURITY.md) - Security considerations

## License

See LICENSE file.
