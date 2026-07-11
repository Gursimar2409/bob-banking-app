"""
conftest.py
-----------
pytest configuration: puts BACKEND/ on sys.path so tests can import
Flask app modules without installing the package.
"""

import os
import sys

# Add BACKEND/ to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BACKEND"))
