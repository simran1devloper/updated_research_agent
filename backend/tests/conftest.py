"""Root conftest — makes shared/ importable for all backend tests."""
import sys
import os

# Allow `import shared` from any test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))
