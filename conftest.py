"""Pytest configuration: ensure project root is importable."""
import sys
import os

# Add project root so `src` package is importable
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)