import sys
import os

# Optional: ensure local imports work when running from PyInstaller
def resource_path(relative_path):
    """Return absolute path of bundled resources (for PyInstaller)"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Import your GUI as the main entry point ---
try:
    import AutoCaptions_gui
except Exception as e:
    print("Failed to load GUI:", e)
    sys.exit(1)

if __name__ == "__main__":
    AutoCaptions_gui.main()    # Your GUI’s entry function
