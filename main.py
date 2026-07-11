"""Android entry point with an early diagnostic fallback."""
import os
import sys
import traceback

_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "mobile"))

try:
    from app import FieldHockeyManagerApp
    _startup_error = None
except Exception:
    FieldHockeyManagerApp = None
    _startup_error = traceback.format_exc()


def _run():
    if FieldHockeyManagerApp is not None:
        FieldHockeyManagerApp().run()
        return

    # This fallback is deliberately defined only after a failed game import,
    # so import-time errors are visible instead of leaving the presplash open.
    from kivy.app import App
    from kivy.core.window import Window
    from kivy.uix.label import Label

    class DiagnosticApp(App):
        def build(self):
            Window.clearcolor = (0.08, 0.02, 0.02, 1)
            message = (_startup_error or "Errore di avvio sconosciuto")[-2400:]
            return Label(
                text="[b]Errore di avvio Field Hockey Manager[/b]\n\n" + message,
                markup=True,
                color=(1, 0.35, 0.35, 1),
                halign="left",
                valign="top",
                text_size=(Window.width - 24, None),
            )

    DiagnosticApp().run()


if __name__ == "__main__":
    _run()
