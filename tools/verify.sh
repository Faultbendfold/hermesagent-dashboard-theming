#!/bin/sh
# verify.sh -- run every check this repository has, in one command.
#
#   ./tools/verify.sh
#
# Checks, in order:
#   1. every Python script compiles
#   2. every shell script is valid POSIX sh
#   3. every theme passes theme-check with warnings treated as errors
#   4. docs/ is byte-identical to what the generators would write
#   5. the tests pass
#
# Exit code 0 means everything is green. This is the script CI runs.

set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname "$here")
cd "$root"

fail=0
step() { printf '\n=== %s\n' "$1"; }

step "python syntax"
for f in skills/hermes-dashboard-theming/scripts/*.py tools/*.py scripts/pair_screenshots.py; do
    [ -e "$f" ] || continue
    if python3 -m py_compile "$f"; then echo "  ok   $f"; else echo "  FAIL $f"; fail=1; fi
done

step "shell syntax"
for f in install.sh tools/verify.sh; do
    if sh -n "$f"; then echo "  ok   $f"; else echo "  FAIL $f"; fail=1; fi
done

step "theme-check (warnings treated as errors)"
if python3 skills/hermes-dashboard-theming/scripts/theme-check.py --strict --quiet themes/*.yaml; then
    echo "  ok   themes/*.yaml"
else
    echo "  FAIL themes/*.yaml"
    fail=1
fi

step "docs/ matches the generators"
if python3 tools/build-gallery.py --check; then :; else fail=1; fi
if python3 tools/gen-schema-doc.py --check; then :; else fail=1; fi

step "unit and integration tests"
if python3 -m unittest discover -s tests; then
    echo "  ok   tests/"
else
    echo "  FAIL tests/"
    fail=1
fi

printf '\n'
if [ "$fail" -eq 0 ]; then
    echo "verify: all checks passed"
else
    echo "verify: FAILURES above"
fi
exit "$fail"
