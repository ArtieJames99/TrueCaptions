import os
import sys
import subprocess
import threading
import time
from PySide6.QtGui import QTextCursor, QIcon  # add this at the top
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QTextEdit,
    QRadioButton,
    QProgressBar,
    QComboBox,
    QSpinBox,
    QMessageBox
)

from PySide6.QtGui import QIcon

def resource_path(relative_path):
    """Get absolute path to resource ."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOCAPTIONS_SCRIPT = os.path.join(SCRIPT_DIR, 'AutoCaptions.py')
DEFAULT_OUT = os.path.join(SCRIPT_DIR, 'transcriptions')
os.makedirs(DEFAULT_OUT, exist_ok=True)  # Ensure default folder exists

# Try a direct import so PyInstaller detects the module during analysis
_STATIC_MP4_TO_SRT = None
try:
    import AutoCaptions as _auto_mod
    _STATIC_MP4_TO_SRT = getattr(_auto_mod, 'mp4_to_srt', None)
except Exception:
    _STATIC_MP4_TO_SRT = None


class Worker(QtCore.QThread):
    log_line = QtCore.Signal(str)
    finished = QtCore.Signal(int)

    def __init__(self, target_func, args=()):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self._stop_requested = False

    def run(self):
        # Run the target function and capture stdout prints by temporarily redirecting sys.stdout
        import sys
        import io

        class StreamCatcher:
            def __init__(self, emit):
                self.emit = emit
            def write(self, s):
                if s:
                    self.emit(s)
            def flush(self):
                pass

        real_stdout = sys.stdout
        catcher = StreamCatcher(lambda s: self.log_line.emit(s))
        sys.stdout = catcher
        try:
            try:
                # Call the transcription function which prints progress lines
                self.target_func(*self.args)
                ret = 0
            except Exception as e:
                import traceback
                self.log_line.emit(f"Error in worker: {e}\n")
                self.log_line.emit(traceback.format_exc())
                ret = 1
        finally:
            sys.stdout = real_stdout
            self.finished.emit(ret)

    def stop(self):
        # mp4_to_srt is not cancelable easily; we set a flag in case we add support later
        self._stop_requested = True


class SubprocessWorker(QtCore.QThread):
    """Run the backend script via an external Python executable and stream stdout to the GUI."""
    log_line = QtCore.Signal(str)
    finished = QtCore.Signal(int)

    def __init__(self, python_exe, script_path, args=None, env=None):
        super().__init__()
        self.python_exe = python_exe
        self.script_path = script_path
        self.args = args or []
        self.env = env or os.environ.copy()
        self._proc = None

    def run(self):
        cmd = [self.python_exe, self.script_path] + self.args
        try:
            # start subprocess and stream stdout line-by-line
            # On Windows, avoid showing a new console window for the child process.
            startupinfo = None
            creationflags = 0
            if sys.platform.startswith('win'):
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    # CREATE_NO_WINDOW prevents a console from being created
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                except Exception:
                    startupinfo = None
            # Open subprocess with explicit text encoding and replace errors so non-decodable bytes don't raise
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=self.env,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                )
            except TypeError:
                # Older Python may not support encoding/errors parameters with Popen; fall back to text mode
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=self.env, text=True, startupinfo=startupinfo, creationflags=creationflags)

            if self._proc.stdout:
                try:
                    for line in self._proc.stdout:
                        # line is a str when text=True; ensure logging never raises
                        try:
                            self.log_line.emit(line.rstrip('\n'))
                        except Exception:
                            # As a last resort, coerce to str safely
                            try:
                                self.log_line.emit(str(line).rstrip('\n'))
                            except Exception:
                                pass
                except Exception as read_exc:
                    import traceback
                    self.log_line.emit(f"Error reading backend output: {read_exc}\n")
                    self.log_line.emit(traceback.format_exc())
            rc = self._proc.wait()
        except Exception as e:
            self.log_line.emit(f"Error launching backend: {e}\n")
            rc = 1
        finally:
            self.finished.emit(rc)

    def stop(self):
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
        except Exception:
            pass


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('TrueCaptions')
        self.resize(400, 550)

        # CSS Styling
        self.setStyleSheet("""
            QPushButton { font-size: 14px; padding: 6px; }
            QProgressBar { height: 20px; border: 1px solid #aaa; border-radius: 8px; }
            QTextEdit { font-family: Consolas; font-size: 12px; background-color: #f5f5f5; color: #000000; }
            QSpinBox, QComboBox, QLineEdit { font-size: 13px; color: #f5f5f5; }
            QTextEdit, QLineEdit, QSpinBox, QComboBox { selection-background-color: #3399ff; selection-color: #ffffff; }
            QLabel { font-weight: bold; }
        """)

        # Widgets
        # Determine a sensible default Python executable. When running from a built exe
        # sys.executable will be the exe itself which is not a usable python interpreter
        # for creating venvs or running pip. Prefer an explicit short-root build venv
        # or a project venv, or an env override `AUTOCAPTIONS_PYTHON` if provided.
        default_python = ''
        env_py = os.environ.get('AUTOCAPTIONS_PYTHON') or os.environ.get('AUTOCAPTIONS_PYENV')
        candidates = []
        if env_py:
            candidates.append(env_py)
        # common short-root venv used by build script
        candidates.append(r'C:\ac_build_venv\Scripts\python.exe')
        # fallback project-local venvs
        candidates.append(os.path.join(SCRIPT_DIR, '.build_venv', 'Scripts', 'python.exe'))
        candidates.append(os.path.join(SCRIPT_DIR, '.venv', 'Scripts', 'python.exe'))
        # last resort: the current executable
        candidates.append(sys.executable)
        for c in candidates:
            try:
                if c and os.path.isfile(c):
                    default_python = c
                    break
            except Exception:
                continue

        self.python_input = QLineEdit(default_python)
        self.python_browse = QPushButton('Browse')
        self.video_input = QLineEdit('')
        self.video_browse = QPushButton('Browse')
        self.out_input = QLineEdit(DEFAULT_OUT)
        self.out_browse = QPushButton('Browse')
        self.mode_normal = QRadioButton('Normal')
        self.mode_line = QRadioButton('Line (short captions)')
        self.mode_normal.setChecked(True)
        self.max_chars = QSpinBox()
        self.max_chars.setRange(5, 200)
        self.max_chars.setValue(15)
        self.model_select = QComboBox()
        self.model_select.addItems(['tiny','small','medium','large'])
        self.model_select.setCurrentText('small')

        self.start_btn = QPushButton('Start')
        self.stop_btn = QPushButton('Stop')
        self.open_out_btn = QPushButton('Open Output Folder')

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        # Layout
        top_layout = QVBoxLayout()
        # If running as a frozen app, hide the Python executable chooser (not applicable)
        if getattr(sys, 'frozen', False):
            info = QLabel('Alma 37:6')
            top_layout.addWidget(info)
        else:
            top_layout.addLayout(self._row_layout('Python executable', self.python_input, self.python_browse))
        top_layout.addLayout(self._row_layout('Video file', self.video_input, self.video_browse))
        top_layout.addLayout(self._row_layout('Output directory', self.out_input, self.out_browse))
        top_layout.addLayout(self._mode_model_layout())
        top_layout.addLayout(self._button_row_layout())
        top_layout.addWidget(QLabel('Log:'))
        top_layout.addWidget(self.log)
        top_layout.addWidget(self.progress)

        self.setLayout(top_layout)

        # Connections
        self.python_browse.clicked.connect(self.browse_python)
        self.video_browse.clicked.connect(self.browse_video)
        self.out_browse.clicked.connect(self.browse_out)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.open_out_btn.clicked.connect(self.open_out)

        self.worker = None

        # import the backend function here to keep module-level imports minimal for PyInstaller
        def _load_backend():
            # Try normal import first
            try:
                import importlib
                mod = importlib.import_module('AutoCaptions')
                self.append_log('AutoCaptions Ready. Please select a video file to start.')
                return getattr(mod, 'mp4_to_srt', None)
            except Exception:
                self.append_log('Normal import of AutoCaptions failed: Please try again or contact support.')

            # Fallback: try loading from known file locations using importlib.util
            try:
                import importlib.util
                candidates = []
                # same folder as this script
                candidates.append(os.path.join(SCRIPT_DIR, 'AutoCaptions.py'))
                # frozen bundle location - prefer this when frozen
                if getattr(sys, 'frozen', False):
                    try:
                        meipass_path = os.path.join(sys._MEIPASS, 'AutoCaptions.py')
                        candidates.insert(0, meipass_path)
                        self.append_log(f'Added frozen candidate path: {meipass_path}')
                    except Exception:
                        pass
                # nested src folder
                candidates.append(os.path.join(SCRIPT_DIR, 'AutoCaptions', 'src', 'AutoCaptions.py'))

                for path in candidates:
                    try:
                        self.append_log(f'Trying backend path: {path}')
                        if path and os.path.isfile(path):
                            spec = importlib.util.spec_from_file_location('autocaptions_dynamic', path)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            self.append_log(f'Backend loaded from file: {path}')
                            return getattr(module, 'mp4_to_srt', None)
                        else:
                            self.append_log(f'Path not found: {path}')
                    except Exception as e:
                        import traceback
                        self.append_log(f'Failed loading {path}: {e}\n')
                        self.append_log(traceback.format_exc())
            except Exception:
                pass

            return None

        self._mp4_to_srt = _load_backend()

    def _row_layout(self, label_text, input_widget, browse_widget):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        layout.addWidget(input_widget)
        layout.addWidget(browse_widget)
        return layout

    def _mode_model_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel('Mode:'))
        layout.addWidget(self.mode_normal)
        layout.addWidget(self.mode_line)
        layout.addStretch()
        layout.addWidget(QLabel('Max chars:'))
        layout.addWidget(self.max_chars)
        layout.addWidget(QLabel('Model:'))
        layout.addWidget(self.model_select)
        return layout

    def _button_row_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.open_out_btn)
        return layout

    def browse_python(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Select Python executable', os.path.dirname(sys.executable), 'Python Executable (*.exe)')
        if p:
            self.python_input.setText(p)

    def browse_video(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Select video file', os.path.expanduser('~'), 'Video Files (*.mp4 *.mov *.mkv)')
        if p:
            self.video_input.setText(p)

    def browse_out(self):
        d = QFileDialog.getExistingDirectory(self, 'Select output directory', DEFAULT_OUT)
        if d:
            self.out_input.setText(d)

    def append_log(self, text):
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.End)

        # parse PROGRESS lines like: PROGRESS: 3/25
        try:
            for line in text.splitlines():
                line = line.strip()
                # parse chunk-level progress printed by backend
                if line.startswith('PROGRESS_CHUNK:'):
                    parts = line.split(':', 1)[1].strip()
                    if '/' in parts:
                        a, b = parts.split('/')
                        try:
                            a = int(a.strip())
                            b = int(b.strip())
                            if b > 0:
                                pct = int(a * 100 / b)
                                self.progress.setValue(pct)
                        except Exception:
                            pass
                    continue
                if line.startswith('PROGRESS:'):
                    parts = line.split(':', 1)[1].strip()
                    if '/' in parts:
                        a, b = parts.split('/')
                        a = int(a.strip())
                        b = int(b.strip())
                        if b > 0:
                            pct = int(a * 100 / b)
                            self.progress.setValue(pct)
        except Exception:
            pass

    def open_out(self):
        out = self.out_input.text() or DEFAULT_OUT
        if not os.path.isdir(out):
            os.makedirs(out, exist_ok=True)
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', out])
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', out])
        else:
            subprocess.Popen(['xdg-open', out])

    def start(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, 'Warning', 'A process is already running!')
            return
        video_file = self.video_input.text()
        out_dir = self.out_input.text() or DEFAULT_OUT
        mode_line = self.mode_line.isChecked()
        max_chars = str(self.max_chars.value())
        model = self.model_select.currentText()

        if not video_file or not os.path.isfile(video_file):
            QMessageBox.warning(self, 'Error', 'Please select a valid video file')
            return

        # set environment variables expected by AutoCaptions
        os.environ['AUTOCAPTIONS_MAXCHARS'] = max_chars
        os.environ['AUTOCAPTIONS_MODEL'] = model
        if out_dir:
            os.environ['AUTOCAPTIONS_OUTDIR'] = out_dir

        if mode_line:
            # also support CLI-style flag read by AutoCaptions
            os.environ['AUTOCAPTIONS_MODE'] = 'line'
        else:
            os.environ.pop('AUTOCAPTIONS_MODE', None)

        # If a Python executable is provided (pyenv) or the app is frozen, run the backend via subprocess
        python_path = self.python_input.text().strip()
        if getattr(sys, 'frozen', False) or (python_path and os.path.isfile(python_path)):
            # Build env for subprocess
            env = os.environ.copy()
            env['AUTOCAPTIONS_MAXCHARS'] = max_chars
            env['AUTOCAPTIONS_MODEL'] = model
            if out_dir:
                env['AUTOCAPTIONS_OUTDIR'] = out_dir
            if mode_line:
                env['AUTOCAPTIONS_MODE'] = 'line'

            # script path: when frozen, try to use the bundled AutoCaptions.py inside _internal or the extracted path
            if getattr(sys, 'frozen', False):
                script_candidates = [os.path.join(sys._MEIPASS, 'AutoCaptions.py'), os.path.join(sys._MEIPASS, 'AutoCaptions', 'src', 'AutoCaptions.py')]
            else:
                script_candidates = [os.path.join(SCRIPT_DIR, 'AutoCaptions.py'), os.path.join(SCRIPT_DIR, 'AutoCaptions', 'src', 'AutoCaptions.py')]

            script_path = None
            for s in script_candidates:
                if s and os.path.isfile(s):
                    script_path = s
                    break

            if not script_path:
                QMessageBox.critical(self, 'Error', 'Backend script not found for subprocess execution')
                return

            self.log.clear()
            self.progress.setValue(0)
            # choose python exe: prefer provided one, else use embedded venv python for build environment
            chosen_python = python_path if python_path and os.path.isfile(python_path) else sys.executable
            self.worker = SubprocessWorker(chosen_python, script_path, args=[video_file] )
            self.worker.log_line.connect(self.append_log)
            self.worker.finished.connect(self._finished)
            self.worker.start()

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            return

        # fallback: run backend inline (same process)
        if not self._mp4_to_srt:
            QMessageBox.critical(self, 'Error', 'Backend import failed: cannot find mp4_to_srt')
            return

        self.log.clear()
        self.progress.setValue(0)
        self.worker = Worker(self._mp4_to_srt, args=(video_file, mode_line))
        self.worker.log_line.connect(self.append_log)
        self.worker.finished.connect(self._finished)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(0)

    def _finished(self, code):
        self.append_log(f"\nProcess finished with code {code}\n")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)


def main():
    # On Windows, set an explicit AppUserModelID so the taskbar groups and icon behave predictably
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.riva.truecaptions')
        except Exception:
            pass

    def _resolved_icon_path():
        # Prefer a bundled icon when frozen; fall back to project files when running from source
        candidates = []
        if getattr(sys, 'frozen', False):
            try:
                candidates.append(os.path.join(sys._MEIPASS, 'sword_of_laban.ico'))
            except Exception:
                pass
        # runtime (source) locations
        candidates.append(os.path.join(SCRIPT_DIR, 'sword_of_laban.ico'))
        for p in candidates:
            try:
                if p and os.path.isfile(p):
                    return p
            except Exception:
                continue
        return None

    app = QApplication(sys.argv)
    # set the application icon (affects titlebar and taskbar)
    icon_path = None
    try:
        icon_path = _resolved_icon_path()
        if icon_path:
            app.setWindowIcon(QIcon(icon_path))
    except Exception:
        icon_path = None

    win = MainWindow()
    try:
        if icon_path:
            win.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
