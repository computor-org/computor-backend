# Scripts Directory

This directory contains various utility scripts organized by purpose.

## 📁 Directory Structure

### `/git-hooks/` ⭐ **Essential**
Git hooks for code quality and security:
- `pre-commit` - Prevents committing secrets (GitLab tokens, API keys, etc.)
- `install-hooks.sh` - Install git hooks into `.git/hooks/`

### `/utilities/` ⭐ **Essential**
General utility scripts for development:
- `ensure_venv.sh` - Ensure virtual environment is activated (used by other scripts)

### Root Level Scripts
Architecture and quality assurance:
- `check_forbidden_imports.py` - Enforce package dependency boundaries (runs on git commit)

### `/debug/` (Optional - for troubleshooting)
Debug tools:
- `debug_gitlab_auth.py` - Test GitLab authentication and API connectivity
- `debug_group_access.py` - Debug GitLab group access issues

### `/testing/` (Optional - for manual testing)
Testing and validation scripts:
- Various GitLab integration test scripts
- `delete_test_gitlab_groups.py` - Clean up GitLab test groups

## 🚀 Usage

### Install Git Hooks (Recommended)
```bash
bash scripts/git-hooks/install-hooks.sh
```

### Code Generation
**Use the unified generator in the project root:**
```bash
bash generate.sh              # Generate all
bash generate.sh types        # Generate TypeScript types
bash generate.sh --help       # Show all options
```

### Check Package Boundaries
```bash
python scripts/check_forbidden_imports.py
python scripts/check_forbidden_imports.py --package computor-types
```

### Debug GitLab Integration
```bash
python scripts/debug/debug_gitlab_auth.py
```

## 📝 Notes

- **Essential scripts**: `/git-hooks/` and `/utilities/` are actively used
- **Optional scripts**: `/debug/` and `/testing/` can be kept or removed based on need
- All scripts should be run from the project root directory
- For code generation, use `bash generate.sh` in the project root
