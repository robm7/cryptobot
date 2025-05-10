"""PyInstaller hook for aiosqlite package."""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('aiosqlite')