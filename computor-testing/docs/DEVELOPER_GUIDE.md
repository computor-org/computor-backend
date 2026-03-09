# Computor Testing Framework - Developer Guide

## Project Overview

This is a pytest-based testing framework for evaluating student code submissions across multiple programming languages. It is used by the backend of the Computor platform at TU Graz.

### Architecture Layers

```
                    CLI Layer (click)
                    ┌─────────────────────────────────────────┐
                    │ computor-test  pytester  octester  etc. │
                    │ blocks         deps-installer  sandbox  │
                    └───────────────────┬─────────────────────┘
                                        │
                    Tester Layer (pytest)
                    ┌───────────────────┴─────────────────────┐
                    │ BaseTester -> PythonTester, CTester, ... │
                    │ conftest_base.py (hooks, report gen)     │
                    │ test_class.py (per-language test logic)  │
                    └───────────────────┬─────────────────────┘
                                        │
                    Executor Layer (subprocess)
                    ┌───────────────────┴─────────────────────┐
                    │ BaseExecutor                             │
                    │ ├── InterpretedExecutor (Py, R, Jl, Oct) │
                    │ └── CompiledExecutor (C, Fortran)        │
                    │ DocumentAnalyzer (no subprocess)         │
                    └───────────────────┬─────────────────────┘
                                        │
                    Core Layer (models, security, helpers)
                    ┌───────────────────┴─────────────────────┐
                    │ ctcore: Pydantic models, path security   │
                    │ ctexec: runtime detection, env handling   │
                    │ sandbox: Docker/local backend, rlimits   │
                    └─────────────────────────────────────────┘
```

### Module Map

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `ctcore/` | Shared Pydantic models, helpers, security | `models.py`, `helpers.py`, `security.py`, `stdio.py` |
| `ctexec/` | Base executor classes, runtime detection | `base.py`, `interpreted.py`, `compiled.py`, `environment.py`, `runtime.py` |
| `testers/` | Language-specific testers, CLI, pytest integration | `base.py`, `cli.py`, `runners.py`, `executors/`, `tests/` |
| `sandbox/` | Execution backends (local, Docker), resource limits | `config.py`, `backends.py`, `executor.py`, `security.py` |
| `blocks/` | Test block definitions for VSCode extension | `models.py`, `cli.py` |
| `dependencies/` | Package dependency management | `models.py`, `installer.py` |

---

## How Tests Execute (End-to-End)

1. **User runs:** `computor-test python run -t student/ -T test.yaml`
2. **CLI** (`testers/cli.py`) creates a `PythonTester` and calls `.run()`
3. **BaseTester.run()** writes a temp specification.yaml and invokes `pytest.main()`
4. **conftest.py** hooks load `test.yaml` and `specification.yaml` into pytest stash
5. **test_class.py::test_computor()** is parametrized with `(main_idx, sub_idx)` pairs
6. For each test case:
   - Executor runs student code in subprocess -> extracts variables via JSON
   - (Optionally) Executor runs reference code the same way
   - Test logic compares actual vs expected values
   - Result is stored in the report structure
7. **Session finish** hook writes `testSummary.json` to the output directory

### Data Flow

```
test.yaml ──┐
             ├──> conftest_base.py ──> pytest parametrize ──> test_class.py
spec.yaml ──┘                                                      │
                                                                    ▼
                                                          PyExecutor.execute()
                                                                    │
                                                                    ▼
                                                        subprocess (wrapper.py)
                                                                    │
                                                                    ▼
                                                          result.json (temp)
                                                                    │
                                                                    ▼
                                                      testSummary.json (output)
```

---

## Adding a New Language

### Step 1: Create an Executor

Create `testers/executors/yourlang.py`:

```python
from ctexec import InterpretedExecutor  # or CompiledExecutor

class YourLangExecutor(InterpretedExecutor):
    language = "yourlang"

    def _get_interpreter_command(self):
        return ["yourlang"]

    def _get_wrapper_extension(self):
        return ".yl"

    def _build_wrapper_script(self, script_path, variables_to_extract,
                              setup_code, teardown_code, input_data, result_path):
        # Build wrapper that:
        # 1. Runs the student script
        # 2. Extracts requested variables
        # 3. Writes JSON to result_path
        ...
```

### Step 2: Register the Executor

In `testers/executors/__init__.py`:
```python
from .yourlang import YourLangExecutor
EXECUTORS["yourlang"] = YourLangExecutor
```

### Step 3: Add Runtime Info

In `ctexec/runtime.py`, add to `RUNTIMES`:
```python
"yourlang": RuntimeInfo(
    name="YourLang",
    language="yourlang",
    binary="yourlang",
    runtime_type=RuntimeType.INTERPRETER,
),
```

### Step 4: Create a Tester Runner

In `testers/runners.py`:
```python
@register_tester
class YourLangTester(BaseTester):
    language = "yourlang"
```

### Step 5: Create Test Infrastructure

Create:
- `testers/tests/yourlang/__init__.py`
- `testers/tests/yourlang/conftest.py` (use `create_conftest_hooks`)
- `testers/tests/yourlang/test_class.py` (implement `test_computor`)

### Step 6: Register CLI

In `testers/__init__.py`, add to `LANGUAGES` dict and update `list_testers()`.
In `testers/cli.py`, add legacy CLI function if needed.
In `pyproject.toml`, add console script entry.

---

## Key Design Decisions

### Property Inheritance

Test properties cascade: `properties` -> `test collection` -> `individual test`.
A `None` value at a lower level inherits from the parent.

**Important:** This inheritance is only fully implemented for Octave (`OctaveTesterConfig`). Other languages use `SimpleTesterConfig` which does NOT inherit. This is a known inconsistency (see AUDIT_REPORT.md).

### Subprocess Isolation

Student code ALWAYS runs in a subprocess, never via in-process `exec()`. This is a critical security boundary. The wrapper script:
1. Changes to the working directory
2. Redirects stdout/stderr
3. Executes the student code
4. Extracts variables and writes JSON to a temp file
5. The parent process reads the JSON

### Environment Security

The `ctexec/environment.py` module provides a minimal safe environment for subprocess execution. Key principles:
- Start with minimal PATH, HOME=/tmp, UTF-8 locale
- Block all known secret patterns (API keys, passwords, tokens)
- Pass through only language-specific variables (PYTHONPATH, R_LIBS_USER, etc.)

### Report Format

The output `testSummary.json` follows the `ComputorReport` Pydantic model:
- Top level: timestamp, type, duration, status, result, summary
- `tests[]`: One entry per test collection (ComputorReportMain)
  - `tests[]`: One entry per individual test (ComputorReportSub)
  - Each has: name, result (PASSED/FAILED/SKIPPED), message

---

## Blocks System

The `blocks/` module defines test types, qualifications, and fields for each language as Pydantic models. These are designed to be exported to JSON Schema and TypeScript for use in the VSCode extension.

### How It Works

```
blocks/models.py (Python definitions)
        │
        ├──> blocks schema   -> JSON Schema (for validation)
        ├──> blocks typescript -> TypeScript interfaces (for VSCode)
        ├──> blocks data     -> Raw JSON (for runtime use)
        └──> blocks templates -> Pre-built YAML snippets
```

### Extending Blocks

To add test types or qualifications for an existing language, edit the relevant `get_*_blocks()` function in `blocks/models.py`. To add a new language, create a new `get_yourlang_blocks()` function and register it in `get_all_blocks()`.

### Current Limitations

- Only Python, C, Octave, and R have block definitions
- Julia, Fortran, and Document are missing
- The blocks module needs significant extension to cover all test types (see AUDIT_REPORT.md section 3.4)

---

## Common Patterns

### Reading test.yaml in test code

```python
_report = item.config.stash[report_key]
testsuite = _report["testsuite"]
specification = _report["specification"]
main_test = testsuite.properties.tests[main_idx]
sub_test = main_test.tests[sub_idx]
```

### Executing student code

```python
from testers.executors import get_executor

executor_class = get_executor("python")
executor = executor_class(working_dir="/path/to/student/code", timeout=30)
result = executor.execute("script.py", variables_to_extract=["x", "y"])
# result.namespace = {"x": 42, "y": [1, 2, 3]}
```

### Path validation

```python
from ctcore.security import validate_path_in_root, safe_join

# Ensure path doesn't escape root
safe_path = validate_path_in_root("student/../../../etc/passwd", root_dir)
# Raises PathValidationError

# Safe path joining
path = safe_join(root_dir, "student", "solution.py")
```

---

## Testing the Framework Itself

```bash
# Install in development mode
pip install -e computor-testing/

# Check all runtimes
computor-test check --all

# Run a test locally
computor-test python run -t ./localTests/correctSolution -T test.yaml -v 2

# Test sandbox backends
sandbox check -v
sandbox test
```

---

## File Naming Conventions

| File | Purpose |
|------|---------|
| `test.yaml` | Test definitions (required) |
| `meta.yaml` | Exercise metadata (optional) |
| `specification.yaml` | Execution configuration (optional, usually auto-generated) |
| `testSummary.json` | Test results output |
| `dependencies.yaml` | Package dependencies for the exercise |

---

## Known Issues & Gotchas

1. **`allowedOccuranceRange`** is misspelled (should be "Occurrence") - this is baked into the API
2. **Property inheritance** only works fully for Octave - other languages silently ignore parent-level settings
3. **The `blocks` module** only covers 4 of 7 languages
4. **Document test types** listed in README are not all in the TypeEnum - they work but aren't validated
5. **Two execution systems** exist (ctexec and sandbox) with overlapping functionality
6. **`meta.yaml` example in README** uses deprecated `slug` field - should be `identifier`
