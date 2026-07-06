import codecs
import ctypes
import locale
import logging
import os
import re
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QTabBar, QStackedWidget, QMenu
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import (
    QFont, QFontDatabase, QTextCursor, QTextCharFormat, QColor,
    QKeyEvent, QDesktopServices, QMouseEvent, QAction
)

from assets.icons import icon
from .conpty import ConPtyProcess

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"([a-z]{2,}:\/\/[^\s\"'<>]+)")
_PATH_RE = re.compile(
    r"((?:[A-Za-z]:)?(?:\\[^\s\"'<>:*/?!]+)+\\?)"
)


def _default_shell() -> str:
    for candidate in [
        os.path.expandvars(r"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"),
        os.environ.get("COMSPEC", ""),
        "cmd.exe",
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    return "cmd.exe"


def _oem_encoding() -> str:
    try:
        oem_cp = ctypes.windll.kernel32.GetOEMCP()
        return f"cp{oem_cp}"
    except Exception:
        return locale.getpreferredencoding()


def _terminal_font(size: int = 12) -> QFont:
    font_file = _find_best_font_file()
    if font_file:
        fid = QFontDatabase.addApplicationFont(font_file)
        if fid >= 0:
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                f = QFont(families[0], size)
                f.setStyleHint(QFont.StyleHint.Monospace)
                return f
    try:
        all_fonts = set(QFontDatabase().families())
    except TypeError:
        all_fonts = set(QFontDatabase.families())
    preferred = [
        "Cascadia Code PL", "Cascadia Mono PL",
        "CaskaydiaCove Nerd Font", "CaskaydiaCove NF",
        "MesloLGS NF", "MesloLGM NF",
        "FiraCode Nerd Font", "Fira Code",
        "JetBrainsMono NF", "JetBrains Mono",
        "Source Code Pro",
    ]
    for family in preferred:
        if family in all_fonts:
            f = QFont(family, size)
            f.setStyleHint(QFont.StyleHint.Monospace)
            return f
    f = QFont("Consolas", size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def _find_best_font_file() -> str | None:
    search_dirs = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
        os.path.expandvars(r"%SystemRoot%\Fonts"),
        os.path.expandvars(r"%USERPROFILE%\Downloads"),
        os.path.expandvars(r"%USERPROFILE%\Desktop"),
    ]
    targets = ["meslolgs nf", "meslolgm nf", "caskaydiacove nf", "caskaydiacove nerd",
               "firacode nerd font", "firacode nf", "jetbrainsmono nf",
               "cascadia code pl", "cascadia mono pl"]
    found = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        try:
            for i, fn in enumerate(os.listdir(d)):
                if i >= 500:
                    break
                low = fn.lower()
                if low.endswith((".ttf", ".otf")):
                    for t in targets:
                        if t in low:
                            found.append((targets.index(t), os.path.join(d, fn)))
                            break
        except Exception:
            pass
    if found:
        found.sort()
        return found[0][1]
    return None


_ANSI_COLORS = [
    "#000000", "#cc0000", "#4e9a06", "#c4a000",
    "#3465a4", "#75507b", "#06989a", "#d3d7cf",
]
_ANSI_BRIGHT = [
    "#555753", "#ef2929", "#8ae234", "#fce94f",
    "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeee",
]
_ANSI_256 = [
    "#000000", "#800000", "#008000", "#808000", "#000080", "#800080", "#008080", "#c0c0c0",
    "#808080", "#ff0000", "#00ff00", "#ffff00", "#0000ff", "#ff00ff", "#00ffff", "#ffffff",
    "#000000", "#00005f", "#000087", "#0000af", "#0000d7", "#0000ff",
    "#005f00", "#005f5f", "#005f87", "#005faf", "#005fd7", "#005fff",
    "#008700", "#00875f", "#008787", "#0087af", "#0087d7", "#0087ff",
    "#00af00", "#00af5f", "#00af87", "#00afaf", "#00afd7", "#00afff",
    "#00d700", "#00d75f", "#00d787", "#00d7af", "#00d7d7", "#00d7ff",
    "#00ff00", "#00ff5f", "#00ff87", "#00ffaf", "#00ffd7", "#00ffff",
    "#5f0000", "#5f005f", "#5f0087", "#5f00af", "#5f00d7", "#5f00ff",
    "#5f5f00", "#5f5f5f", "#5f5f87", "#5f5faf", "#5f5fd7", "#5f5fff",
    "#5f8700", "#5f875f", "#5f8787", "#5f87af", "#5f87d7", "#5f87ff",
    "#5faf00", "#5faf5f", "#5faf87", "#5fafaf", "#5fafd7", "#5fafff",
    "#5fd700", "#5fd75f", "#5fd787", "#5fd7af", "#5fd7d7", "#5fd7ff",
    "#5fff00", "#5fff5f", "#5fff87", "#5fffaf", "#5fffd7", "#5fffff",
    "#870000", "#87005f", "#870087", "#8700af", "#8700d7", "#8700ff",
    "#875f00", "#875f5f", "#875f87", "#875faf", "#875fd7", "#875fff",
    "#878700", "#87875f", "#878787", "#8787af", "#8787d7", "#8787ff",
    "#87af00", "#87af5f", "#87af87", "#87afaf", "#87afd7", "#87afff",
    "#87d700", "#87d75f", "#87d787", "#87d7af", "#87d7d7", "#87d7ff",
    "#87ff00", "#87ff5f", "#87ff87", "#87ffaf", "#87ffd7", "#87ffff",
    "#af0000", "#af005f", "#af0087", "#af00af", "#af00d7", "#af00ff",
    "#af5f00", "#af5f5f", "#af5f87", "#af5faf", "#af5fd7", "#af5fff",
    "#af8700", "#af875f", "#af8787", "#af87af", "#af87d7", "#af87ff",
    "#afaf00", "#afaf5f", "#afaf87", "#afafaf", "#afafd7", "#afafff",
    "#afd700", "#afd75f", "#afd787", "#afd7af", "#afd7d7", "#afd7ff",
    "#afff00", "#afff5f", "#afff87", "#afffaf", "#afffd7", "#afffff",
    "#d70000", "#d7005f", "#d70087", "#d700af", "#d700d7", "#d700ff",
    "#d75f00", "#d75f5f", "#d75f87", "#d75faf", "#d75fd7", "#d75fff",
    "#d78700", "#d7875f", "#d78787", "#d787af", "#d787d7", "#d787ff",
    "#d7af00", "#d7af5f", "#d7af87", "#d7afaf", "#d7afd7", "#d7afff",
    "#d7d700", "#d7d75f", "#d7d787", "#d7d7af", "#d7d7d7", "#d7d7ff",
    "#d7ff00", "#d7ff5f", "#d7ff87", "#d7ffaf", "#d7ffd7", "#d7ffff",
    "#ff0000", "#ff005f", "#ff0087", "#ff00af", "#ff00d7", "#ff00ff",
    "#ff5f00", "#ff5f5f", "#ff5f87", "#ff5faf", "#ff5fd7", "#ff5fff",
    "#ff8700", "#ff875f", "#ff8787", "#ff87af", "#ff87d7", "#ff87ff",
    "#ffaf00", "#ffaf5f", "#ffaf87", "#ffafaf", "#ffafd7", "#ffafff",
    "#ffd700", "#ffd75f", "#ffd787", "#ffd7af", "#ffd7d7", "#ffd7ff",
    "#ffff00", "#ffff5f", "#ffff87", "#ffffaf", "#ffffd7", "#ffffff",
    "#080808", "#121212", "#1c1c1c", "#262626", "#303030", "#3a3a3a",
    "#444444", "#4e4e4e", "#585858", "#626262", "#6c6c6c", "#767676",
    "#808080", "#8a8a8a", "#949494", "#9e9e9e", "#a8a8a8", "#b2b2b2",
    "#bcbcbc", "#c6c6c6", "#d0d0d0", "#dadada", "#e4e4e4", "#eeeeee",
]


class _TerminalInput(QLineEdit):
    execute = pyqtSignal(str)
    keyUp = pyqtSignal()
    keyDown = pyqtSignal()
    ctrlC = pyqtSignal()
    clearRequested = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent | None):
        if event is None:
            return
        if event.key() == Qt.Key.Key_Up and self.text().strip():
            self.keyUp.emit()
        elif event.key() == Qt.Key.Key_Down:
            self.keyDown.emit()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            self.ctrlC.emit()
        elif event.key() == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.clearRequested.emit()
        else:
            super().keyPressEvent(event)


class _TerminalOutput(QTextEdit):
    linkClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._links: dict[tuple[int, int], str] = {}

    def mousePressEvent(self, event: QMouseEvent | None):
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            pos = cursor.position()
            for (start, end), url in self._links.items():
                if start <= pos <= end:
                    self.linkClicked.emit(url)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None):
        if event is None:
            return
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        over_link = any(s <= pos <= e for s, e in self._links)
        self.viewport().setCursor(
            Qt.CursorShape.PointingHandCursor if over_link else Qt.CursorShape.IBeamCursor
        )
        super().mouseMoveEvent(event)

    def insert_links(self, text: str) -> str:
        self._links.clear()
        result = text
        offset = 0
        for pattern in (_URL_RE, _PATH_RE):
            for m in pattern.finditer(text):
                url = m.group(0)
                start = m.start() + offset
                end = m.end() + offset
                self._links[(start, end)] = url
        return result


class _TerminalSession(QWidget):
    output_received = pyqtSignal(object)

    def __init__(self, shell: str, cwd: str, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.cwd = cwd
        self.process: QProcess | None = None
        self._conpty: ConPtyProcess | None = None
        self._use_conpty = False
        self._history: list[str] = []
        self._history_index = -1
        self._utf8_ready = False
        self._utf8_grace_until = 0.0
        self._sys_enc = _oem_encoding()
        self._fallback_encs = []
        seen = set()
        for enc in (self._sys_enc, locale.getpreferredencoding(), "cp1251", "cp1252", "latin-1"):
            if enc not in seen:
                seen.add(enc)
                self._fallback_encs.append(enc)
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        name = os.path.basename(shell).lower()
        self._is_powershell = "powershell" in name or "pwsh" in name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output = _TerminalOutput()
        self.output.setReadOnly(True)
        self.output.setObjectName("terminal-output")
        self.output.setStyleSheet("""
            QTextEdit#terminal-output {
                background-color: #0a0a0a;
                color: #c9d1d9;
                border: none;
                padding: 4px 8px;
                font-size: 13px;
            }
        """)
        term_font = _terminal_font(12)
        self.output.setFont(term_font)
        layout.addWidget(self.output, 1)

        input_row = QWidget()
        input_row.setObjectName("terminal-input-row")
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(8, 2, 8, 4)
        input_layout.setSpacing(4)

        self._prompt = QLabel(">")
        self._prompt.setStyleSheet("color: #3fb950; font-weight: 700; font-size: 13px;")
        input_layout.addWidget(prompt)

        self.input = _TerminalInput()
        self.input.setObjectName("terminal-input")
        self.input.returnPressed.connect(self._execute)
        self.input.keyUp.connect(self._history_up)
        self.input.keyDown.connect(self._history_down)
        self.input.ctrlC.connect(self._interrupt)
        self.input.clearRequested.connect(self.clear_output)
        self.input.setStyleSheet("""
            QLineEdit#terminal-input {
                background: transparent;
                border: none;
                color: #c9d1d9;
                font-size: 13px;
                padding: 2px 0;
            }
        """)
        mono_input = _terminal_font(12)
        self.input.setFont(mono_input)
        input_layout.addWidget(self.input, 1)

        layout.addWidget(input_row)

        self._start()

    def _start(self):
        if self._conpty and self._conpty.is_running():
            return
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            return
        # Try ConPTY first (Win10 1809+), fall back to QProcess pipes
        self._try_conpty()
        if not self._use_conpty:
            self._start_qprocess()
        if not self._use_conpty and not (self.process and self.process.state() == QProcess.ProcessState.Running):
            logger.error(f"Terminal session failed to start with shell: {self.shell}")

    def _try_conpty(self):
        cp = ConPtyProcess()
        try:
            cp.start(
                shell=self.shell,
                cwd=self.cwd,
                cols=80, rows=25,
                on_output=self._on_conpty_raw,
                on_exit=self._on_conpty_exit,
            )
            self.output_received.connect(self._on_conpty_output)
            self._conpty = cp
            self._use_conpty = True
            QTimer.singleShot(200, self._activate_venv)
        except Exception:
            try:
                cp.close()
            except Exception:
                pass
            self._use_conpty = False
            self._conpty = None

    def _on_conpty_raw(self, data: bytes):
        self.output_received.emit(data)

    def _on_conpty_output(self, data: bytes):
        try:
            text = data.decode(self._sys_enc, errors="replace")
        except LookupError:
            text = data.decode("utf-8", errors="replace")
        self._print(text)

    def _on_conpty_exit(self):
        self._conpty = None
        self._use_conpty = False

    def _start_qprocess(self):
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.finished.connect(self._on_finished)
        self.process.started.connect(self._switch_to_utf8)
        self.process.setWorkingDirectory(self.cwd)
        self.process.start(self.shell)

    def _switch_to_utf8(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            if self._is_powershell:
                self.process.write(
                    "chcp 65001 | Out-Null; "
                    "$OutputEncoding = [Console]::OutputEncoding = "
                    "[System.Text.Encoding]::UTF8; "
                    "$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'; "
                    "function global:prompt { "
                    "'PS ' + $executionContext.SessionState.Path.CurrentLocation "
                    "+ '>' * ($nestedPromptLevel + 1) + ' ' }\r\n".encode()
                )
            else:
                self.process.write("chcp 65001 >NUL\r\n".encode())
        QTimer.singleShot(500, self._mark_utf8_ready)

    def _mark_utf8_ready(self):
        self._utf8_ready = True
        self._utf8_grace_until = time.monotonic() + 0.5
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.output.clear()
        self._activate_venv()

    def _activate_venv(self):
        venv_dir = os.path.join(self.cwd, "venv")
        if not os.path.isdir(venv_dir):
            return
        data = b""
        if self._is_powershell:
            ps_activate = os.path.join(venv_dir, "Scripts", "Activate.ps1")
            if os.path.isfile(ps_activate):
                m = (
                    '. "' + ps_activate + '"\r\n'
                    'function prompt { "'
                    '\x1b[93m(VENV) \x1b[0m'
                    'PS $($executionContext.SessionState.Path.CurrentLocation)'
                    "$('>' * ($nestedPromptLevel + 1)) \" }\r\n"
                )
                data = m.encode("utf-8")
        else:
            bat = os.path.join(venv_dir, "Scripts", "activate.bat")
            if os.path.isfile(bat):
                m = f'"{bat}"\r\n' 'prompt \x1b[93m(VENV) \x1b[0m$P$G\r\n'
                data = m.encode("utf-8")
        if data:
            if self._use_conpty and self._conpty:
                self._conpty.write(data)
            elif self.process and self.process.state() == QProcess.ProcessState.Running:
                self.process.write(data)

    def _execute(self, text: str | None = None):
        if text is None:
            text = self.input.text().strip()
            if not text:
                return
            self.input.clear()
            self._history.append(text)
            self._history_index = len(self._history)
        else:
            if not text.strip():
                return
        cmd = text + "\r\n"
        data = cmd.encode("utf-8")
        if self._use_conpty and self._conpty:
            self._conpty.write(data)
        elif self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write(data)

    def _on_output(self):
        if not self.process:
            return
        raw = bytes(self.process.readAllStandardOutput())
        if not raw:
            return
        if self._utf8_ready:
            text = self._decoder.decode(raw)
            if "\ufffd" in text:
                self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
                # Count replacement chars ratio — only fall back if most data is garbled
                ratio = text.count("\ufffd") / max(len(text), 1)
                if ratio > 0.10:
                    best = raw.decode("utf-8", errors="replace")
                    for enc in self._fallback_encs:
                        try:
                            cand = raw.decode(enc, errors="replace")
                        except LookupError:
                            continue
                        if "\ufffd" not in cand and "\ufffd" in best:
                            best = cand
                    text = best
                # else: keep UTF-8 result despite a few stray bad bytes
            self._print(text)
        else:
            text = raw.decode(self._sys_enc, errors="replace")
            self._print(text)

    def _print(self, text: str):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        self._insert_ansi(cursor, text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _insert_ansi(self, cursor: QTextCursor, text: str):
        fmt = QTextCharFormat()
        i = 0
        while i < len(text):
            if text[i] != "\x1b":
                chunk = ""
                j = i
                while j < len(text) and text[j] != "\x1b":
                    chunk += text[j]
                    j += 1
                cursor.insertText(chunk, fmt)
                i = j
                continue
            # Escape sequence
            if i + 1 >= len(text):
                break
            if text[i + 1] == "[":
                # CSI: \x1b[ ... <final byte 0x40-0x7E>
                j = i + 2
                while j < len(text) and not (0x40 <= ord(text[j]) <= 0x7E):
                    j += 1
                if j < len(text):
                    final = text[j]
                    params = text[i + 2:j]
                    if final == "m":
                        self._apply_sgr(fmt, params)
                    elif final == "J":
                        if params in ("", "0", "2"):
                            cursor.select(QTextCursor.SelectionType.Document)
                            cursor.removeSelectedText()
                    elif final == "K":
                        if params in ("", "0"):
                            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                            cursor.removeSelectedText()
                        elif params == "2":
                            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
                            cursor.removeSelectedText()
                i = j + 1
            elif text[i + 1] == "]":
                # OSC: \x1b] ... \x07 or \x1b\\
                j = i + 2
                while j < len(text) and text[j] != "\x07":
                    if text[j] == "\x1b" and j + 1 < len(text) and text[j + 1] == "\\":
                        j += 2
                        break
                    j += 1
                else:
                    j += 1  # skip \x07
                i = j
            else:
                # Other escape: skip 2 chars
                i += 2

    @staticmethod
    def _apply_sgr(fmt: QTextCharFormat, params: str):
        if not params:
            params = "0"
        try:
            codes = [int(c) if c else 0 for c in params.split(";")]
        except ValueError:
            return
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                fmt.setForeground(QColor(self._fg0))
                fmt.setBackground(QColor())
                fmt.setFontWeight(QFont.Weight.Normal)
            elif c == 1:
                fmt.setFontWeight(QFont.Weight.Bold)
            elif c == 22:
                fmt.setFontWeight(QFont.Weight.Normal)
            elif 30 <= c <= 37:
                fmt.setForeground(QColor(_ANSI_COLORS[c - 30]))
            elif c == 39:
                fmt.setForeground(QColor(self._fg0))
            elif 40 <= c <= 47:
                fmt.setBackground(QColor(_ANSI_COLORS[c - 40]))
            elif c == 49:
                fmt.setBackground(QColor())
            elif c == 100:
                fmt.setBackground(QColor(self._fg2))
            elif 101 <= c <= 107:
                fmt.setBackground(QColor(_ANSI_BRIGHT[c - 101]))
            elif c == 90:
                fmt.setForeground(QColor("#808080"))
            elif 91 <= c <= 97:
                fmt.setForeground(QColor(_ANSI_BRIGHT[c - 91]))
            elif c == 38 and i + 1 < len(codes):
                if codes[i + 1] == 5 and i + 2 < len(codes):
                    idx = codes[i + 2]
                    if 0 <= idx < 256:
                        fmt.setForeground(QColor(_ANSI_256[idx]))
                    i += 2
                elif codes[i + 1] == 2 and i + 4 < len(codes):
                    fmt.setForeground(QColor(codes[i + 2], codes[i + 3], codes[i + 4]))
                    i += 4
                i += 1
            elif c == 48 and i + 1 < len(codes):
                if codes[i + 1] == 5 and i + 2 < len(codes):
                    idx = codes[i + 2]
                    if 0 <= idx < 256:
                        fmt.setBackground(QColor(_ANSI_256[idx]))
                    i += 2
                elif codes[i + 1] == 2 and i + 4 < len(codes):
                    fmt.setBackground(QColor(codes[i + 2], codes[i + 3], codes[i + 4]))
                    i += 4
                i += 1
            i += 1

    def _interrupt(self):
        if self._use_conpty and self._conpty:
            self._conpty.write(b"\x03")
            self._print("\n")
        elif self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write(b"\x03")
            self._print("\n")

    def _on_finished(self, exit_code, exit_status):
        self._print(f"\n[Process exited with code {exit_code}]\n")

    def _history_up(self):
        if not self._history:
            return
        if self._history_index > 0:
            self._history_index -= 1
            self.input.setText(self._history[self._history_index])

    def _history_down(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.input.setText(self._history[self._history_index])
        else:
            self._history_index = len(self._history)
            self.input.clear()

    def execute_direct(self, cmd: str):
        data = (cmd + "\r\n").encode("utf-8")
        if self._use_conpty and self._conpty:
            self._conpty.write(data)
        elif self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write(data)

    def cd(self, path: str):
        if self._is_powershell:
            self.execute_direct(f'cd "{path}"')
        else:
            self.execute_direct(f'cd /d "{path}"')

    def clear_output(self):
        self.output.clear()

    def focus_input(self):
        self.input.setFocus()

    def terminate(self):
        if self._use_conpty and self._conpty:
            self._conpty.close()
            self._conpty = None
            self._use_conpty = False
        elif self.process:
            try:
                self.process.kill()
            except Exception:
                pass


class TerminalWidget(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("terminal-widget")
        self._sessions: list[_TerminalSession] = []
        self._default_cwd = os.getcwd()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar
        tab_row = QWidget()
        tab_row.setObjectName("terminal-tab-row")
        tab_row.setFixedHeight(30)
        tab_layout = QHBoxLayout(tab_row)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        self._tab_bar = QTabBar()
        self._tab_bar.setObjectName("terminal-tab-bar")
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setMovable(True)
        self._tab_bar.setDocumentMode(True)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.tabCloseRequested.connect(self._close_session)
        self._tab_bar.currentChanged.connect(self._switch_session)
        tab_layout.addWidget(self._tab_bar, 1)

        self._add_btn = QPushButton("+")
        self._add_btn.setObjectName("terminal-add-btn")
        self._add_btn.setFixedSize(22, 22)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setToolTip("New terminal")
        self._add_btn.clicked.connect(lambda _: self._add_session())
        tab_layout.addWidget(self._add_btn)

        tab_layout.addStretch()

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("terminal-clear-btn")
        self._clear_btn.setFixedHeight(22)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setToolTip("Clear terminal output")
        self._clear_btn.clicked.connect(lambda _: self._clear_terminal())
        tab_layout.addWidget(self._clear_btn)

        self._close_panel_btn = QPushButton()
        self._close_panel_btn.setIcon(icon("x"))
        self._close_panel_btn.setObjectName("terminal-close-btn")
        self._close_panel_btn.setFixedSize(22, 22)
        self._close_panel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_panel_btn.setToolTip("Close panel")
        self._close_panel_btn.clicked.connect(lambda: self.setVisible(False))
        self._close_panel_btn.clicked.connect(lambda: self.toggled.emit(False))
        tab_layout.addWidget(self._close_panel_btn)

        layout.addWidget(tab_row)

        # Session stack
        self._stack = QStackedWidget()
        self._stack.setObjectName("terminal-stack")
        layout.addWidget(self._stack, 1)

        self.setStyleSheet(self._styles())

        # Start with one session
        self._add_session()

    def _add_session(self, shell: str | None = None, cwd: str | None = None):
        if shell is None:
            shell = _default_shell()
        if cwd is None:
            cwd = self._default_cwd
        name = os.path.basename(shell).replace(".exe", "").upper()
        existing = [self._tab_bar.tabText(i) for i in range(self._tab_bar.count())]
        if name in existing:
            count = sum(1 for e in existing if e.startswith(name))
            name = f"{name} ({count + 1})"

        session = _TerminalSession(shell, cwd)
        session.output.linkClicked.connect(self._open_link)
        self._sessions.append(session)
        idx = self._stack.addWidget(session)
        self._tab_bar.addTab(name)
        self._tab_bar.setCurrentIndex(idx)
        self._stack.setCurrentIndex(idx)
        QTimer.singleShot(50, session.focus_input)

    def _close_session(self, index: int):
        if self._tab_bar.count() <= 1:
            self._clear_terminal()
            return
        session = self._sessions.pop(index)
        session.terminate()
        self._stack.removeWidget(session)
        session.deleteLater()
        self._tab_bar.removeTab(index)

    def _switch_session(self, index: int):
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)
            session = self._sessions[index]
            QTimer.singleShot(50, session.focus_input)

    def _clear_terminal(self):
        session = self._current_session()
        if session:
            session.clear_output()

    def _open_link(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def _current_session(self) -> _TerminalSession | None:
        idx = self._stack.currentIndex()
        if 0 <= idx < len(self._sessions):
            return self._sessions[idx]
        return None

    def set_workdir(self, path: str):
        self._default_cwd = path
        for session in self._sessions:
            session.cd(path)

    def focus_input(self):
        session = self._current_session()
        if session:
            session.focus_input()

    def _styles(self) -> str:
        v = _THEME_VARS["dark" if self._dark else "light"]
        return f"""
            QWidget#terminal-tab-row {
                background-color: {v["bg0"]};
                border-bottom: 1px solid {v["border"]};
            }
            QTabBar#terminal-tab-bar {
                background: transparent;
                border: none;
                qproperty-drawBase: 0;
            }
            QTabBar#terminal-tab-bar::tab {
                background: {v["bg0"]};
                color: {v["fg2"]};
                padding: 4px 14px;
                font-size: 11px;
                font-weight: 600;
                border: none;
                border-right: 1px solid {v["border"]};
                min-height: 26px;
            }
            QTabBar#terminal-tab-bar::tab:selected {
                color: {v["fg0"]};
                background: {v["bg2"]};
            }
            QTabBar#terminal-tab-bar::tab:hover:!selected {
                color: {v["fg0"]};
                background: {v["bg4"]};
            }
            QTabBar#terminal-tab-bar::close-button {
                width: 14px;
                height: 14px;
                margin: 0 0 0 6px;
            }
            QTabBar#terminal-tab-bar::close-button:hover {
                background: {v["bg3"]};
                border-radius: 2px;
            }
            QPushButton#terminal-add-btn {
                background: transparent;
                border: none;
                color: {v["fg2"]};
                font-size: 16px;
                font-weight: 700;
                margin: 0 2px;
                border-radius: 2px;
            }
            QPushButton#terminal-add-btn:hover {
                background: {v["bg3"]};
                color: {v["fg0"]};
            }
            QPushButton#terminal-clear-btn, QPushButton#terminal-close-btn {
                background: transparent;
                border: none;
                border-radius: 2px;
                color: {v["fg2"]};
                margin: 0 1px;
            }
            QPushButton#terminal-clear-btn:hover, QPushButton#terminal-close-btn:hover {
                background: {v["bg3"]};
                color: {v["fg0"]};
            }
        """
