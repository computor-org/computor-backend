# Computor Testing Framework

A pytest-based testing framework for evaluating code submissions in multiple languages, designed for educational use at TU Graz.

## Supported Languages

| Language | Command | Test Types |
|----------|---------|------------|
| Python | `computor-test python run` | variable, graphics, stdout, structural |
| Octave/MATLAB | `computor-test octave run` | variable, graphics, structural |
| R | `computor-test r run` | variable, stdout, structural |
| Julia | `computor-test julia run` | variable, stdout, structural |
| C/C++ | `computor-test c run` | stdout, exitcode, compile |
| Fortran | `computor-test fortran run` | stdout, exitcode, compile |
| Document/Text | `computor-test document run` | wordcount, linecount, keyword, section |

## Features

- **Variable Testing**: Compare student variables against reference values with configurable tolerances
- **stdout Testing**: Compare program output (C, Fortran, Python, R, Julia)
- **Graphics Testing**: Verify graphical output properties (axes, labels, data)
- **Structural Testing**: Check for specific keywords/constructs in code
- **Document Testing**: Analyze text files for word count, structure, keywords, and more
- **Existence Tests**: Verify required files exist
- **Token Exchange**: Dynamic file/command substitution in test code
- **Success Dependencies**: Chain tests based on previous results
- **Path Security**: Validation against directory traversal attacks

## Installation

The package depends on `computor-types` from the same repository, which is not
published on PyPI. From the root of a `computor-backend` checkout:

```bash
# Install both packages
pip install ./computor-types ./computor-testing

# Or for development (editable mode)
pip install -e ./computor-types -e ./computor-testing
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
        - name: for              # Octave counts the keyword given as name
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
| `stdout` | C, Fortran, Python, R, Julia | Compare program output |
| `graphics` | Octave, Python | Check graphical properties |
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
│   ├── runners.py    # Language-specific tester classes
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
│   ├── launch.py     # Landlock/seccomp launcher for student processes
│   └── cli.py        # sandbox CLI
├── blocks/           # Test YAML generation tools
├── dependencies/     # Package management
└── pyproject.toml    # Package configuration
```

## Execution Limits and Sandbox

Every student process started by a tester gets resource limits, which can be
tuned through environment variables (`0` disables a limit):

| Variable | Limit | Default |
|----------|-------|---------|
| `COMPUTOR_JOB_CPU_SECONDS` | CPU time per process | 60 |
| `COMPUTOR_JOB_MEMORY_BYTES` | Address space | 2 GiB |
| `COMPUTOR_JOB_MAX_PROCESSES` | Processes of the user (RLIMIT_NPROC) | 512 |
| `COMPUTOR_JOB_MAX_FILE_SIZE` | Size of a written file | 64 MiB |
| `COMPUTOR_JOB_MAX_OPEN_FILES` | Open files | 256 |

With `COMPUTOR_SANDBOX_ENABLE=1`, as set by the testing worker, each student
process additionally runs under the kernel sandbox in `sandbox/launch.py`
(see [SECURITY.md](SECURITY.md)). Local runs leave it off.

The `sandbox` CLI is a separate tool for trying commands under a local or
Docker backend; its `CT_RUNNER_*` variables (`sandbox env`) configure only that
CLI, not the testers:

```bash
sandbox check
sandbox test
```

## meta.yaml Configuration

The `meta.yaml` file describes the example when it is uploaded to the platform
(model `CodeAbilityMeta` in `computor-types`):

```yaml
slug: physics.c.hello_world
version: '1.0'
title: Hello World in C
description: A simple Hello World program
language: en
license: CC BY-NC 4.0
keywords: [c, basics]

authors:
  - name: Your Name
    email: your.email@example.org
    affiliation: Your Institute

properties:
  studentSubmissionFiles:
    - hello.c
  executionBackend:
    language: c
```

`executionBackend` names either a `language` (python, octave, r, julia, c,
cpp, fortran, document, matlab), which the platform matches against its
registered test runners, optionally with a `version`, or a `slug` that pins one
specific runner. `settings` is accepted and stored with the example but is not
applied by the testers; set timeouts and compiler options in `test.yaml`.

## Assignment Directory Structure

```
assignment/
├── test.yaml              # Test definitions
├── meta.yaml              # Metadata (required for upload to the platform)
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
  "status": "COMPLETED",
  "result": "PASSED",
  "resultMessage": "Congratulations! All tests passed",
  "tests": [
    {
      "name": "Variable Tests",
      "type": "variable",
      "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
      "tests": [
        {"name": "result", "status": "COMPLETED", "result": "PASSED"}
      ]
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
- [Blocks README](blocks/README.md) - Block system for VSCode extension
- [Dependencies README](dependencies/README.md) - Dependency management
- [Security](SECURITY.md) - How student code is isolated

## License

See LICENSE file.

## Acknowledgements

This project is built on top of [catester](https://github.com/trigonal-mike/catester),
which is licensed under the MIT License.

Copyright (c) trigonal-mike