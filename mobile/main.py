"""Entry point for the Kivy mobile UI."""
import sys
import os

# Ensure project root and mobile are importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "mobile"))

from app import FieldHockeyManagerApp

if __name__ == "__main__":
    FieldHockeyManagerApp().run()