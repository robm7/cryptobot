import os
import shutil
import platform
import PyInstaller.__main__

def clean_build():
    """Remove previous build artifacts"""
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def build_executable():
    """Build standalone executable using PyInstaller"""
    args = [
        'app.py',
        '--onefile',
        '--name=cryptobot',
        '--add-data=templates;templates',
        '--add-data=static;static',
        '--hidden-import=flask',
        '--hidden-import=flask_socketio',
        '--hidden-import=ccxt',
        '--clean'
    ]
    
    PyInstaller.__main__.run(args)

def package_for_platform():
    """Create platform-specific distribution package"""
    system = platform.system().lower()
    
    if system == 'windows':
        shutil.make_archive(f'cryptobot-windows', 'zip', 'dist')
    elif system == 'linux':
        shutil.make_archive(f'cryptobot-linux', 'gztar', 'dist')
    elif system == 'darwin':
        shutil.make_archive(f'cryptobot-macos', 'zip', 'dist')

if __name__ == '__main__':
    print("Starting build process...")
    clean_build()
    build_executable()
    package_for_platform()
    print("Build completed successfully!")