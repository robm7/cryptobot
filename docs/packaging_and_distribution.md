# Packaging and Distribution Guide

This guide explains how to package and distribute the Cryptobot trading system as a standalone executable.

## Overview

Cryptobot can be packaged as a standalone executable using PyInstaller, which bundles the Python interpreter, all required libraries, and the application code into a single package. This makes it easy to distribute and run the application without requiring users to install Python or any dependencies.

## Prerequisites

Before packaging Cryptobot, ensure you have the following:

- Python 3.8 or higher
- pip (Python package manager)
- Git (for version control)
- PowerShell (for Windows) or Bash (for Linux)
- Internet connection (for downloading dependencies)

## Build Scripts

Cryptobot includes build scripts for both Windows and Linux:

- **Windows**: `scripts/build_windows.ps1`
- **Linux**: `scripts/build_linux.sh`

These scripts handle the entire build process, including:

1. Creating a virtual environment
2. Installing dependencies
3. Running PyInstaller
4. Creating distribution archives

## Building on Windows

To build Cryptobot on Windows:

1. Open PowerShell
2. Navigate to the Cryptobot project directory
3. Run the build script:

```powershell
# Navigate to project directory
cd path\to\cryptobot

# Run the build script
.\scripts\build_windows.ps1
```

### Build Options

The Windows build script supports several options:

- `-Clean`: Clean build and dist directories before building
- `-Optimize`: Optimize the build for size using UPX
- `-Test`: Run the executable after building to verify it works

Example with options:

```powershell
.\scripts\build_windows.ps1 -Clean -Optimize
```

## Building on Linux

To build Cryptobot on Linux:

1. Open a terminal
2. Navigate to the Cryptobot project directory
3. Make the build script executable (if needed)
4. Run the build script:

```bash
# Navigate to project directory
cd path/to/cryptobot

# Make the script executable (if needed)
chmod +x scripts/build_linux.sh

# Run the build script
./scripts/build_linux.sh
```

### Build Options

The Linux build script supports several options:

- `--clean`: Clean build and dist directories before building
- `--optimize`: Optimize the build for size using UPX
- `--test`: Run the executable after building to verify it works

Example with options:

```bash
./scripts/build_linux.sh --clean --optimize
```

## Build Outputs

The build process creates the following outputs in the `dist` directory:

- **Directory-based executable**: A directory containing the executable and all dependencies
  - Windows: `dist/cryptobot/cryptobot.exe`
  - Linux: `dist/cryptobot/cryptobot`

- **Single-file executable**: A single executable file that extracts dependencies at runtime
  - Windows: `dist/cryptobot_onefile.exe`
  - Linux: `dist/cryptobot_onefile`

- **Distribution archive**: An archive containing the directory-based executable
  - Windows: `dist/cryptobot-windows.zip`
  - Linux: `dist/cryptobot-linux.tar.gz`

## Running the Packaged Application

### Windows

To run the packaged application on Windows:

```
# Directory-based executable
dist\cryptobot\cryptobot.exe [options]

# Single-file executable
dist\cryptobot_onefile.exe [options]
```

### Linux

To run the packaged application on Linux:

```
# Directory-based executable
./dist/cryptobot/cryptobot [options]

# Single-file executable
./dist/cryptobot_onefile [options]
```

## Command-Line Options

The packaged application supports the following command-line options:

- `--config`: Path to configuration file
- `--dashboard`: Run the dashboard
- `--cli`: Run the command-line interface
- `--service`: Run a specific service (auth, strategy, data, trade, backtest)
- `--all`: Run all services
- `--version`: Show version information

Example:

```
cryptobot.exe --config my_config.json --all
```

## Dependency Management

Cryptobot includes a dependency management script that helps manage project dependencies:

```
python scripts/manage_dependencies.py [options]
```

Options:

- `--update`: Update dependencies to latest versions
- `--check`: Check for security vulnerabilities
- `--generate`: Generate requirements.txt with pinned versions
- `--report`: Generate dependency report
- `--all`: Perform all actions

## Configuration

The packaged application uses the configuration file specified with the `--config` option. If no configuration file is specified, it uses the default configuration.

You can create a custom configuration file by copying and modifying the default configuration:

```
config/default_config.json
```

## Troubleshooting

### Missing Dependencies

If the packaged application fails to run due to missing dependencies, try the following:

1. Ensure all dependencies are listed in `requirements.txt`
2. Add the missing dependency to the `hidden_imports` list in `pyinstaller_config.spec`
3. Rebuild the application

### Antivirus False Positives

Some antivirus software may flag PyInstaller-packaged applications as suspicious. This is a known issue with PyInstaller. To resolve this:

1. Add the executable to your antivirus whitelist
2. Use a code signing certificate to sign the executable (recommended for production)

### Linux Permissions

On Linux, ensure the executable has execute permissions:

```bash
chmod +x dist/cryptobot/cryptobot
chmod +x dist/cryptobot_onefile
```

## Distribution

### Windows

To distribute the application on Windows:

1. Share the single-file executable (`cryptobot_onefile.exe`)
2. Or share the ZIP archive (`cryptobot-windows.zip`)

### Linux

To distribute the application on Linux:

1. Share the single-file executable (`cryptobot_onefile`)
2. Or share the tarball archive (`cryptobot-linux.tar.gz`)

## Advanced Customization

### Custom PyInstaller Hooks

If you need to customize how PyInstaller packages certain modules, you can add custom hooks in the `hooks` directory.

### Code Signing

For production distribution, it's recommended to sign the executable with a code signing certificate:

#### Windows

```powershell
# Sign the executable using signtool
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\cryptobot_onefile.exe
```

#### Linux

```bash
# Sign the executable using gpg
gpg --output dist/cryptobot_onefile.sig --detach-sig dist/cryptobot_onefile
```

## Continuous Integration

You can integrate the build process into your CI/CD pipeline:

### Testing Distribution Packages

Before distributing the application, it's important to test the packages to ensure they work correctly. Cryptobot includes a test script that verifies the distribution packages:

```bash
# Test Windows package
python scripts/test_distribution.py --platform windows

# Test Linux package
python scripts/test_distribution.py --platform linux

# Test macOS package
python scripts/test_distribution.py --platform macos

# Test all packages
python scripts/test_distribution.py --platform all
```

The test script performs the following checks:
1. Extracts the distribution package
2. Verifies that the executable runs correctly
3. Checks that all required dependencies and resources are included

### Automated Build Process

Cryptobot includes a unified build script that can build installers for all supported platforms:

```bash
# Build all installers
python scripts/build_all_installers.py

# Build Windows installer only
python scripts/build_all_installers.py --platform windows

# Build Linux installer only (both DEB and RPM)
python scripts/build_all_installers.py --platform linux

# Build Linux DEB installer only
python scripts/build_all_installers.py --platform linux --linux-type deb

# Build with optimization
python scripts/build_all_installers.py --optimize

# Clean build directories before building
python scripts/build_all_installers.py --clean

# Test installers after building
python scripts/build_all_installers.py --test
```

### GitHub Actions Integration

A GitHub Actions workflow is included in the `.github/workflows/build.yml` file. This workflow automatically builds and tests the distribution packages for all supported platforms when changes are pushed to the main branches or when a new tag is created.

The workflow performs the following steps:
1. Builds the executables for Windows, Linux, and macOS
2. Tests the distribution packages
3. Uploads the artifacts
4. Creates a release when a new tag is pushed

```yaml
name: Build and Test

on:
  push:
    branches: [ main, master, develop ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main, master, develop ]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          cache: 'pip'
      - name: Build Windows executable
        run: .\scripts\build_windows.ps1 -Clean -Optimize
      - name: Test Windows executable
        run: python scripts/test_distribution.py --platform windows
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: cryptobot-windows
          path: dist/cryptobot-windows.zip

  # Similar jobs for Linux and macOS...

  create-release:
    needs: [build-windows, build-linux, build-macos]
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            artifacts/cryptobot-windows/cryptobot-windows.zip
            artifacts/cryptobot-linux/cryptobot-linux.tar.gz
            artifacts/cryptobot-macos/CryptoBot.dmg
```

## Conclusion

By following this guide, you can package and distribute Cryptobot as a standalone executable for Windows, Linux, and macOS platforms. The automated build and test process ensures that the distribution packages work correctly across all supported platforms. This makes it easy for users to run the application without installing Python or any dependencies.