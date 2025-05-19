import sys
import os

# Add project root to sys.path to allow for absolute imports of top-level packages
# when 'auth' package or its submodules are imported.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Clean up to avoid polluting the namespace of modules importing this __init__
del sys, os, PROJECT_ROOT