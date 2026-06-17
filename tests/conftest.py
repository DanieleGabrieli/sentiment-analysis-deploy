import sys
import os

# Make sure the app package is importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
