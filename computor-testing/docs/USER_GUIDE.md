# Computor Testing Framework - User Guide

This guide is for **exercise authors** who write test.yaml files and use the framework to test student submissions.

---

## Quick Start

### 1. Install

From the root of a `computor-backend` checkout (`computor-types` is not on PyPI):

```bash
pip install -e ./computor-types -e ./computor-testing
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
├── meta.yaml                  # Metadata (required for upload to the platform)
├── content/
│   └── index_en.md            # Assignment text, one file per language
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

The cascade applies in all testers to `qualification`, `relativeTolerance`,
`absoluteTolerance`, `typeCheck`, `shapeCheck`, `ignoreClass` and `verbosity`,
and from `properties:` to the collections also to `timeout`,
`storeGraphicsArtifacts` and `competency`. `allowedOccuranceRange` and
`occuranceType` are not inherited; set them on each test that needs them.

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
    - "x = 10"                     # Python and Octave: runs after the entry point
    - "y = compute(x)"
  tearDownCode:
    - "cleanup()"                  # Runs after setUpCode, before variables are read
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

Available for: C, Fortran, Python, R, Julia

```yaml
- type: stdout
  name: Output Tests
  entryPoint: main.c
  tests:
    - name: greeting
      qualification: contains      # Check output contains this
      pattern: "Hello"

    - name: exact
      qualification: matches       # Exact match
      value: "Hello, World!\n"

    - name: pattern
      qualification: regexp        # Regex match
      pattern: "Result: \\d+"

    - name: prefix
      qualification: startsWith
      pattern: "Program"

    - name: suffix
      qualification: endsWith
      pattern: "Done."
```

Without a `qualification`, the output is compared with `value` or, if no
`value` is given, with the output of the reference solution. C and Fortran
trim the output before comparing and also accept `value` in place of
`pattern`. Python compares the untrimmed output and takes the expected text
for every qualification, including `matches`, from `pattern`. R and Julia
support `contains` and `regexp` (and treat `matches` as a regular expression).

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
      allowedOccuranceRange: [1, 0]  # At least once, no upper limit

    - name: for_loop
      pattern: "\\bfor\\b"
      allowedOccuranceRange: [2, 5]  # Must appear 2-5 times
```

**Note on `allowedOccuranceRange`:** The format is `[min, max]`:

| Value | Meaning |
| --- | --- |
| `[0, 0]` | The item must **not** occur at all |
| `[n, 0]` (n > 0) | At least `n` occurrences, no upper limit |
| `[min, max]` | Between `min` and `max` occurrences, inclusive |

Alternatively, `countRequirement: n` asserts an exact count. It applies only when
`allowedOccuranceRange` is not set; a sub-test with neither is skipped.

For Python, `name` is matched against the token stream, so dotted names such as
`np.pi` are counted as a unit and matches inside comments and strings are
ignored. Supplying a `pattern` instead switches to a regex over the raw file
text, which does include comments and strings.

R and Julia count `pattern` (or `name`) in the same way. Octave ignores
`pattern` and counts the keyword or function given as `name`. C and Fortran
apply the range to known keywords given as `name` (such as `for` or
`malloc`); for any other test they only check that `pattern` (or `name`)
occurs in the source.

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

### graphics - Plot Testing (Python, Octave)

Each `name` is an expression evaluated after the script has run. In Python it
is prefixed with `plt.`; in Octave it is evaluated as written. The result is
compared with `value` or with the reference solution.

```yaml
- type: graphics
  name: Plot Tests
  entryPoint: plot_script.py
  tests:
    - name: gcf().axes[0].get_xlabel()
      value: "Time"
    - name: gcf().axes[0].get_title()
      value: "Data Plot"
```

```yaml
- type: graphics
  name: Plot Tests
  entryPoint: plot_script.m
  tests:
    - name: get(gca, 'XLim')
      value: [0, 10]
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

In Octave tests, files found by earlier `exist` tests can be referenced as
`#file_N#` (file name, counted from 1) in the `file` of a structural test:

```yaml
- type: exist
  name: Script
  tests:
    - name: "*.m"                  # Whatever .m file the student submitted

- type: structural
  name: Loops
  file: "#file_1#"                 # Replaced with the file found above
  tests:
    - name: for
      allowedOccuranceRange: [1, 0]
```

---

## meta.yaml

Metadata of the example, required when it is uploaded to the platform. The
tester itself reads only `properties.testDependencies`.

```yaml
slug: physics.python.hello_world  # Unique, dot-separated identifier
version: '1.0'
title: Hello World in Python
description: A simple Hello World program
language: en
license: CC BY-NC 4.0
keywords: [python, basics]         # Shown as tags in the example library
category: Basics

authors:
  - name: Your Name
    email: your.email@example.org
    affiliation: Your Institute

properties:
  studentSubmissionFiles:
    - solution.py
  executionBackend:
    language: python
    version: "3.12"
```

`executionBackend` takes either a `language` (python, octave, r, julia, c,
cpp, fortran, document, matlab), matched against the test runners of the
installation, with an optional `version`, or a `slug` that pins one specific
runner. Its `settings` are stored but not applied by the testers; set
`timeout` and compiler options in `test.yaml`.

---

## CLI Reference

### Unified CLI

```bash
# Run tests
computor-test <language> run -t <student_dir> -T <test.yaml> [-v 0-3]

# Local testing (test.yaml in the parent directory or in <solution_dir>)
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
- Check that the packages your code imports are installed on the platform's test runner; the platform does not read `dependencies.yaml`
- Verify `executionBackend` in meta.yaml names a language or runner the installation provides

### "Execution failed" with no further message

Each student process runs with resource limits. `COMPUTOR_JOB_MAX_PROCESSES`
(default 512) counts all processes and threads of your user, so on a busy
workstation local runs can fail to start the interpreter. Set
`COMPUTOR_JOB_MAX_PROCESSES=0` for local runs.

### "Path validation failed"

The framework prevents directory traversal attacks. Ensure:
- No `..` in file paths
- All paths are relative to the test root directory
- Entry points reference files within the student/reference directories

### Output not captured

For interpreted languages, make sure the entry point script actually produces output. For compiled languages, make sure `printf`/`cout` flushes output (use `\n` or `fflush(stdout)`).
