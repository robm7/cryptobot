#!/bin/bash
# Run coverage tests and generate HTML report
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
python "$SCRIPT_DIR/run_coverage_tests.py" "$@"