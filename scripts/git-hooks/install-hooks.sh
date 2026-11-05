#!/usr/bin/env bash
# Script to install git hooks for the project

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "🔧 Installing git hooks..."

# In a worktree .git is a file. Use the shared git dir, not --git-path hooks,
# which follows a global core.hooksPath and would overwrite hooks of all repos.
if ! GIT_COMMON_DIR="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
    echo "❌ Error: Not in a git repository!"
    exit 1
fi
GIT_HOOKS_DIR="$GIT_COMMON_DIR/hooks"

# Create hooks directory if it doesn't exist
mkdir -p "$GIT_HOOKS_DIR"

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit" ]; then
    echo "📋 Installing pre-commit hook..."
    cp "$SCRIPT_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit"
    chmod +x "$GIT_HOOKS_DIR/pre-commit"
    echo "✅ Pre-commit hook installed"
else
    echo "⚠️  Warning: pre-commit hook not found in $SCRIPT_DIR"
fi

# Future: Add more hooks here as needed
# Example:
# if [ -f "$SCRIPT_DIR/pre-push" ]; then
#     cp "$SCRIPT_DIR/pre-push" "$GIT_HOOKS_DIR/pre-push"
#     chmod +x "$GIT_HOOKS_DIR/pre-push"
# fi

echo
echo "✅ Git hooks installation complete!"
echo
echo "The following protections are now active:"
echo "  🔒 Pre-commit: Prevents committing secrets (GitLab tokens, API keys, etc.)"
echo
echo "To bypass hooks in emergency (NOT RECOMMENDED):"
echo "  git commit --no-verify"
echo
echo "To uninstall hooks:"
echo "  rm $GIT_HOOKS_DIR/pre-commit"