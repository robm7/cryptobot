# Run coverage tests and generate HTML report
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptPath "run_coverage_tests.py"
python $pythonScript $args