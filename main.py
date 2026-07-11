"""Entry point for buildozer/Android — delegates to mobile UI."""
import sys
import os

_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "mobile"))

from app import FieldHockeyManagerApp

if __name__ == "__main__":
    FieldHockeyManagerApp().run()