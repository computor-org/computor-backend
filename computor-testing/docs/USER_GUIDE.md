# Computor Testing Framework - User Guide

This guide is for **exercise authors** who write test.yaml files and use the framework to test student submissions.

---

## Quick Start

### 1. Install

```bash
pip install -e /path/to/computor-testing
```

### 2. Check your environment

```bash
computor-test check --all
```

### 3. Create a test.yaml

```bash
# Use the blocks CLI to generate a starter file
blocks init -l python -n "My Exercise Tests"

# Or create manually (see examples below)
```

### 4. Run tests

```bash
computor-test python run -t ./student -T test.yaml
```

---

## Directory Structure

Your exercise directory should look like:

```
my-exercise/
├── test.yaml                  # Test definitions (required)
├── meta.yaml                  # Metadata (optional)
├── reference/                 # Reference solution
│   └── solution.py
├── localTests/
│   ├── correctSolution/       # Should pass all tests
│   │   └── solution.py
│   └── wrongSolution/         # Should fail some tests
│       └── solution.py
└── output/
    └── testSummary.json       # Generated test results
```

---

## Writing test.yaml

### Basic Structure

```yaml
name: Exercise Name
description: What this exercise tests
type: python           # python, octave, r, julia, c, fortran, document
version: "1.0"

properties:
  relativeTolerance: 1e-12    # Default for numeric comparisons
  absoluteTolerance: 0.0001
  timeout: 180                # Seconds

  tests:
    - type: exist             # Test collection
      name: File Check
      tests:
        - name: solution.py   # Individual test

    - type: variable
      name: Variable Tests
      entryPoint: solution.py
      tests:
        - name: result
          value: 42
```

### Property Cascade

Properties set at the `properties:` level serve as defaults. They can be overridden at the test collection level, which can be overridden at the individual test level.

> **Note:** Full property inheritance (parent -> child cascade) currently only works for Octave tests. For other languages, always set properties at the level where you need them.

---

## Test Types

### exist - File Existence

Available for ALL languages. Checks that required files exist.

```yaml
- type: exist
  name: Required Files
  tests:
    - name: solution.py          # Exact filename
    - name: data/*.csv           # Glob pattern
    - name: config.json
      allowEmpty: true           # Allow 0-byte files (default: false)
```

### variable - Variable Comparison

Available for: Python, Octave, R, Julia

Runs a script and compares workspace variables against expected values.

```yaml
- type: variable
  name: Computation Tests
  entryPoint: solution.py          # Script to execute
  tests:
    - name: result                 # Variable name
      value: 42                    # Expected value

    - name: matrix
      value: [[1, 2], [3, 4]]     # Arrays/matrices

    - name: pi_approx
      value: 3.14159
      relativeTolerance: 1e-4     # Override default tolerance

    - name: greeting
      value: "Hello, World!"
```

#### With Setup/Teardown Code

```yaml
- type: variable
  name: Advanced Tests
  entryPoint: solution.py
  setUpCode:
    - "x = 10"                     # Run before checking variables
    - "y = compute(x)"
  tearDownCode:
    - "cleanup()"                  # Run after checking
  tests:
    - name: y
      value: 100
```

#### With Input (stdin)

```yaml
- type: variable
  name: Interactive Tests
  entryPoint: solution.py
  inputAnswers:
    - "5"                          # First input() call gets "5"
    - "hello"                      # Second input() call gets "hello"
  tests:
    - name: result
      value: 5
```

### stdout - Output Comparison

Available for: C, Fortran (primary), Python, Octave, R, Julia

```yaml
- type: stdout
  name: Output Tests
  entryPoint: main.c
  tests:
    - name: greeting
      qualification: contains      # Check output contains this
      value: "Hello"

    - name: exact
      qualification: matches       # Exact match
      value: "Hello, World!\n"

    - name: pattern
      qualification: regexp        # Regex match
      value: "Result: \\d+"

    - name: prefix
      qualification: startsWith
      value: "Program"

    - name: suffix
      qualification: endsWith
      value: "Done."
```

### structural - Code Structure

Available for ALL languages. Checks for keywords/patterns in source code.

```yaml
- type: structural
  name: Code Structure
  file: solution.py                # File to analyze
  tests:
    - name: no_eval                # Descriptive name
      pattern: "\\beval\\b"        # Regex pattern to search
      allowedOccuranceRange: [0, 0]  # Must appear 0 times (forbidden)

    - name: uses_function
      pattern: "\\bdef\\b"
      allowedOccuranceRange: [1, 0]  # Must appear at least once (0 = no upper limit)

    - name: for_loop
      pattern: "\\bfor\\b"
      allowedOccuranceRange: [2, 5]  # Must appear 2-5 times
```

**Note on `allowedOccuranceRange`:** The format is `[min, max]`. A `max` of `0` means "no upper limit".

### exitcode - Exit Code Check (C, Fortran)

```yaml
- type: exitcode
  name: Exit Code
  entryPoint: main.c
  tests:
    - name: success
      expectedExitCode: 0

    - name: error_case
      expectedExitCode: 1
```

### compile - Compilation Test (C, Fortran)

```yaml
- type: compile
  name: Compilation
  entryPoint: main.c
  compiler: gcc
  compilerFlags: ["-Wall", "-Wextra", "-Werror"]
  tests:
    - name: compiles_clean         # Should compile without errors
```

### graphics - Plot Testing (Octave only)

```yaml
- type: graphics
  name: Plot Tests
  entryPoint: plot_script.m
  tests:
    - name: has_xlabel
    - name: has_ylabel
    - name: has_title
```

### Document Test Types

Available for: Document

```yaml
type: document

properties:
  tests:
    - type: wordcount
      name: Word Count
      file: essay.md
      tests:
        - name: minimum_words
          allowedOccuranceRange: [500, 0]   # At least 500 words

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
          allowedOccuranceRange: [3, 0]     # At least 3 occurrences

    - type: linecount
      name: Line Count
      file: essay.md
      tests:
        - name: minimum_lines
          allowedOccuranceRange: [50, 0]
```

---

## Success Dependencies

You can make test collections depend on previous ones:

```yaml
properties:
  tests:
    - type: exist
      name: File Check
      id: file_check              # Give it an ID
      tests:
        - name: solution.py

    - type: variable
      name: Variable Tests
      entryPoint: solution.py
      successDependency: file_check   # Only runs if File Check passed
      tests:
        - name: result
          value: 42
```

---

## Token Exchange

For Octave tests, you can use tokens that get replaced with actual filenames:

```yaml
- type: variable
  name: File Processing
  entryPoint: "#file_1#"           # Gets replaced with actual student file
  tests:
    - name: data
      value: [1, 2, 3]
```

---

## meta.yaml

Optional metadata for the exercise:

```yaml
identifier: itpcp.pgph.python.hello_world
version: '1.0'
title: Hello World in Python
description: A simple Hello World program
license: CC BY-NC 4.0

authors:
  - name: Your Name
    email: your.email@tugraz.at
    affiliation: TU Graz

properties:
  studentSubmissionFiles:
    - solution.py
  executionBackend:
    slug: itpcp.exec.python
    version: "3.12"
    settings:
      timeout: 60
      memoryLimitMB: 256
```

---

## CLI Reference

### Unified CLI

```bash
# Run tests
computor-test <language> run -t <student_dir> -T <test.yaml> [-v 0-3]

# Local testing (auto-finds test.yaml)
computor-test <language> local -d <solution_dir>

# Check runtime
computor-test check --all
computor-test check python

# List available testers
computor-test list
```

### Blocks CLI (test.yaml generation)

```bash
# List available test types
blocks list -l python

# Initialize a new test.yaml
blocks init -l python -n "My Tests"

# Generate a test snippet
blocks generate -l python -t variable -n result

# Browse templates
blocks templates list
blocks templates show "Variable Check" -l python

# Export for VSCode extension
blocks export ./generated
```

### Sandbox CLI

```bash
# Check backends
sandbox check -v

# Run a command in sandbox
sandbox run python3 -c "print('hello')"

# Show configuration
sandbox config --show

# Test sandbox functionality
sandbox test
```

### Dependency Installer

```bash
# Install all dependencies
deps-installer install -f dependencies.yaml

# Generate Dockerfile
deps-installer dockerfile -f dependencies.yaml -o Dockerfile

# Validate dependencies file
deps-installer validate -f dependencies.yaml
```

---

## Troubleshooting

### "Runtime not found"

```bash
# Check which runtimes are available
computor-test check --all

# For R, make sure jsonlite is installed:
Rscript -e "install.packages('jsonlite', repos='https://cloud.r-project.org/')"

# For Julia, make sure JSON is installed:
julia -e 'import Pkg; Pkg.add("JSON")'
```

### Tests pass locally but fail on server

- Check timeout values - server may be slower
- Ensure no hardcoded absolute paths in test.yaml
- Check that all required packages are in dependencies.yaml
- Verify the execution backend settings in meta.yaml

### "Path validation failed"

The framework prevents directory traversal attacks. Ensure:
- No `..` in file paths
- All paths are relative to the test root directory
- Entry points reference files within the student/reference directories

### Output not captured

For interpreted languages, make sure the entry point script actually produces output. For compiled languages, make sure `printf`/`cout` flushes output (use `\n` or `fflush(stdout)`).
