#!/bin/bash
#
# Integration test for computor-testing framework.
# Runs all examples in examples/ through their respective testers
# and reports pass/fail per language.
#
# Usage:
#   ./scripts/integration_test.sh           # run all languages
#   ./scripts/integration_test.sh python c  # run specific languages
#
# Requires: computor-testing installed (pip install -e .)
# For R tests: R_LIBS_USER must point to a library with jsonlite installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXAMPLES_DIR="$PROJECT_DIR/examples"

# Language config: directory suffix -> tester command
declare -A LANG_MAP=(
    [py]=python
    [oct]=octave
    [jl]=julia
    [r]=r
    [c]=c
    [f]=fortran
    [doc]=document
)

# Counters
total=0
passed=0
failed=0
errors=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

run_example() {
    local tester="$1"
    local example_dir="$2"
    local name
    name=$(basename "$example_dir")

    # Find correctSolution directory
    local sol_dir=""
    if [ -d "$example_dir/localTests/correctSolution" ]; then
        sol_dir="$example_dir/localTests/correctSolution"
    elif [ -d "$example_dir/localTests/_correctSolution" ]; then
        sol_dir="$example_dir/localTests/_correctSolution"
    fi

    if [ -z "$sol_dir" ]; then
        printf "  %-50s ${YELLOW}SKIP (no correctSolution)${RESET}\n" "$name"
        return 0
    fi

    if [ ! -f "$example_dir/test.yaml" ]; then
        printf "  %-50s ${YELLOW}SKIP (no test.yaml)${RESET}\n" "$name"
        return 0
    fi

    total=$((total + 1))

    # Run tester, capture last line for summary
    local output
    output=$(computor-test "$tester" run -t "$sol_dir" -T "$example_dir/test.yaml" 2>&1)
    local exit_code=$?
    local summary
    summary=$(echo "$output" | tail -1)

    # Check for failures in pytest output
    if echo "$summary" | grep -q "failed"; then
        failed=$((failed + 1))
        printf "  %-50s ${RED}FAIL${RESET}  %s\n" "$name" "$summary"
        return 1
    elif echo "$summary" | grep -qE "passed|skipped"; then
        passed=$((passed + 1))
        printf "  %-50s ${GREEN}OK${RESET}    %s\n" "$name" "$summary"
        return 0
    elif [ $exit_code -ne 0 ]; then
        errors=$((errors + 1))
        printf "  %-50s ${RED}ERROR${RESET} exit code %d\n" "$name" "$exit_code"
        return 1
    else
        passed=$((passed + 1))
        printf "  %-50s ${GREEN}OK${RESET}    %s\n" "$name" "$summary"
        return 0
    fi
}

run_language() {
    local suffix="$1"
    local tester="${LANG_MAP[$suffix]}"
    local lang_dir="$EXAMPLES_DIR/itpcp.pgph.$suffix"

    if [ ! -d "$lang_dir" ]; then
        return
    fi

    printf "\n${CYAN}=== %s ===${RESET}\n" "$(echo "$tester" | tr '[:lower:]' '[:upper:]')"

    local lang_fail=0
    for example_dir in "$lang_dir"/*/; do
        [ -d "$example_dir" ] || continue
        run_example "$tester" "$example_dir" || lang_fail=1
    done

    return $lang_fail
}

# Determine which languages to test
if [ $# -gt 0 ]; then
    # Map full names back to suffixes
    declare -A NAME_TO_SUFFIX=(
        [python]=py [py]=py
        [octave]=oct [oct]=oct
        [julia]=jl [jl]=jl
        [r]=r
        [c]=c
        [fortran]=f [f]=f
        [document]=doc [doc]=doc
    )
    languages=()
    for arg in "$@"; do
        key=$(echo "$arg" | tr '[:upper:]' '[:lower:]')
        if [ -n "${NAME_TO_SUFFIX[$key]+x}" ]; then
            languages+=("${NAME_TO_SUFFIX[$key]}")
        else
            echo "Unknown language: $arg"
            echo "Available: python, octave, julia, r, c, fortran, document"
            exit 1
        fi
    done
else
    languages=(c f doc oct jl r py)
fi

# Run tests
any_fail=0
for suffix in "${languages[@]}"; do
    run_language "$suffix" || any_fail=1
done

# Summary
printf "\n${CYAN}=== SUMMARY ===${RESET}\n"
printf "Total: %d  Passed: ${GREEN}%d${RESET}  Failed: ${RED}%d${RESET}  Errors: ${RED}%d${RESET}\n" \
    "$total" "$passed" "$failed" "$errors"

if [ $any_fail -ne 0 ] || [ $failed -gt 0 ] || [ $errors -gt 0 ]; then
    printf "\n${RED}INTEGRATION TEST FAILED${RESET}\n"
    exit 1
else
    printf "\n${GREEN}ALL INTEGRATION TESTS PASSED${RESET}\n"
    exit 0
fi
