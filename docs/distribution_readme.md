# CryptoBot Distribution Guide

This document provides a quick reference for building, testing, and distributing CryptoBot packages.

> **Note for Unix-like systems (Linux/macOS)**: Make sure to make the scripts executable before running them:
> ```bash
> chmod +x scripts/*.py scripts/*.sh
> ```

## Quick Start

### Building Distribution Packages

To build distribution packages for all supported platforms:

```bash
# Build all installers
python scripts/build_all_installers.py
```

### Platform-Specific Builds

```bash
# Windows
.\scripts\build_windows.ps1 -Clean -Optimize

# Linux
./scripts/build_linux.sh --clean --optimize

# macOS
./scripts/build_macos_app.sh --clean --optimize
./scripts/build_macos_dmg.sh
```

### Testing Distribution Packages

```bash
# Test all packages
python scripts/test_distribution.py --platform all

# Test specific platform
python scripts/test_distribution.py --platform windows
python scripts/test_distribution.py --platform linux
python scripts/test_distribution.py --platform macos
```

## Build Outputs

The build process creates the following outputs in the `dist` directory:

### Windows
- Directory-based executable: `dist/cryptobot/cryptobot.exe`
- Single-file executable: `dist/cryptobot_onefile.exe`
- ZIP archive: `dist/cryptobot-windows.zip`

### Linux
- Directory-based executable: `dist/cryptobot/cryptobot`
- Single-file executable: `dist/cryptobot_onefile`
- Tarball archive: `dist/cryptobot-linux.tar.gz`
- DEB package: `dist/cryptobot_1.0.0_amd64.deb` (if built with `build_linux_deb.sh`)
- RPM package: `dist/cryptobot-1.0.0-1.x86_64.rpm` (if built with `build_linux_rpm.sh`)

### macOS
- Application bundle: `dist/CryptoBot.app`
- DMG installer: `dist/CryptoBot.dmg`

## Continuous Integration

The project includes a GitHub Actions workflow in `.github/workflows/build.yml` that automatically builds and tests the distribution packages for all supported platforms when changes are pushed to the main branches or when a new tag is created.

To create a new release:

1. Tag the commit with a version number:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

2. The GitHub Actions workflow will automatically build the packages, test them, and create a release with the distribution packages attached.

## Troubleshooting

### Missing Dependencies

If the packaged application fails to run due to missing dependencies:

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

## Advanced Configuration

### Custom PyInstaller Hooks

If you need to customize how PyInstaller packages certain modules, you can add custom hooks in the `hooks` directory.

### Code Signing

For production distribution, it's recommended to sign the executable with a code signing certificate:

#### Windows
```powershell
# Sign the executable using signtool
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\cryptobot_onefile.exe
```

#### macOS
```bash
# Sign the application using codesign
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/CryptoBot.app
```

#### Linux
```bash
# Sign the executable using gpg
gpg --output dist/cryptobot_onefile.sig --detach-sig dist/cryptobot_onefile
```

## Further Reading

For more detailed information, refer to the following documents:

- [Packaging and Distribution Guide](packaging_and_distribution.md)
- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)