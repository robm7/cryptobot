@echo off
echo Running dependency update script...
python %~dp0\update_dependencies.py
if %ERRORLEVEL% EQU 0 (
    echo Dependency update completed successfully.
) else (
    echo Dependency update failed with error code %ERRORLEVEL%.
)
pause