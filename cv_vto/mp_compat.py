"""
Import MediaPipe even when matplotlib cannot load.

MediaPipe imports matplotlib.pyplot at start-up, but only uses it for one plotting helper
(plot_landmarks) that this project never calls. On some Windows computers a security policy
blocks matplotlib's compiled files ("DLL load failed ... Application Control policy"), which
then stops MediaPipe too. If that happens we register a harmless stand-in so MediaPipe loads.
"""
import sys
import types


def import_mediapipe():
    try:
        import matplotlib.pyplot  # noqa: F401  (just checking that it loads)
    except Exception:
        for name in [m for m in sys.modules if m == "matplotlib" or m.startswith("matplotlib.")]:
            del sys.modules[name]
        stub = types.ModuleType("matplotlib")
        stub.pyplot = types.ModuleType("matplotlib.pyplot")
        stub.__path__ = []
        sys.modules["matplotlib"] = stub
        sys.modules["matplotlib.pyplot"] = stub.pyplot
    import mediapipe as mp
    return mp
