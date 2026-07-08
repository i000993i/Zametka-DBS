import ctypes
import ctypes.wintypes
import logging
import os
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabBar, QStackedWidget, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon

from assets.icons import icon

logger = logging.getLogger(__name__)

# Win32 constants
CREATE_NEW_CONSOLE = 0x00000010
CREATE_NO_WINDOW = 0x08000000
SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9
WM_CLOSE = 0x0010
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_BORDER = 0x00800000
WS_DLGFRAME = 0x00400000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32


class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", ctypes.wintypes.HANDLE),
        ("hThread", ctypes.wintypes.HANDLE),
        ("dwProcessId", ctypes.wintypes.DWORD),
        ("dwThreadId", ctypes.wintypes.DWORD),
    ]


class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("lpReserved", ctypes.wintypes.LPWSTR),
        ("lpDesktop", ctypes.wintypes.LPWSTR),
        ("lpTitle", ctypes.wintypes.LPWSTR),
        ("dwX", ctypes.wintypes.DWORD),
        ("dwY", ctypes.wintypes.DWORD),
        ("dwXSize", ctypes.wintypes.DWORD),
        ("dwYSize", ctypes.wintypes.DWORD),
        ("dwXCountChars", ctypes.wintypes.DWORD),
        ("dwYCountChars", ctypes.wintypes.DWORD),
        ("dwFillAttribute", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("wShowWindow", ctypes.wintypes.WORD),
        ("cbReserved2", ctypes.wintypes.WORD),
        ("lpReserved2", ctypes.wintypes.LPBYTE),
        ("hStdInput", ctypes.wintypes.HANDLE),
        ("hStdOutput", ctypes.wintypes.HANDLE),
        ("hStdError", ctypes.wintypes.HANDLE),
    ]


def _default_shell() -> str:
    for candidate in [
        os.path.expandvars(r"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"),
        os.environ.get("COMSPEC", ""),
        "cmd.exe",
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    return "cmd.exe"


def _find_console_window(pid, timeout=5.0):
    """Find the console window HWND for a given process ID."""
    deadline = time.monotonic() + timeout
    hwnds = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum_proc(hwnd, _lparam):
        hwnds.append(hwnd)
        return True

    while time.monotonic() < deadline:
        hwnds.clear()
        user32.EnumWindows(_enum_proc, 0)
        for hwnd in hwnds:
            pid_buf = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_buf))
            if pid_buf.value != pid:
                continue
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value == "ConsoleWindowClass":
                return hwnd
        time.sleep(0.1)
    return None


class NativeTerminalSession:
    def __init__(self, shell: str, cwd: str, container_hwnd: int):
        self._shell = shell
        self._cwd = cwd
        self._container_hwnd = container_hwnd
        self._hwnd = None
        self._hProcess = None
        self._hThread = None
        self._pid = 0
        self._is_powershell = "powershell" in shell.lower()
        self._start()

    def _start(self):
        shell = self._shell
        cwd = self._cwd or os.getcwd()

        si = _STARTUPINFOW()
        si.cb = ctypes.sizeof(_STARTUPINFOW)
        si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
        si.wShowWindow = SW_HIDE  # Start hidden, we'll show it after SetParent

        pi = _PROCESS_INFORMATION()

        cmd = f'"{shell}"'
        created = kernel32.CreateProcessW(
            None, cmd,
            None, None, False,
            CREATE_NEW_CONSOLE,
            None, cwd,
            ctypes.byref(si), ctypes.byref(pi),
        )
        if not created:
            logger.error(f"Failed to start {shell}")
            return

        self._hProcess = pi.hProcess
        self._hThread = pi.hThread
        self._pid = pi.dwProcessId

        # Wait for console window to appear
        hwnd = _find_console_window(self._pid)
        if not hwnd:
            logger.error("Could not find console window")
            return

        self._hwnd = hwnd

        # Embed into our container
        user32.SetParent(hwnd, self._container_hwnd)

        # Remove title bar and borders
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER | WS_DLGFRAME
                   | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)

        # Show the window
        user32.ShowWindow(hwnd, SW_SHOW)

        # Give it a moment to render
        QTimer.singleShot(100, lambda: self._resize())

    def _resize(self):
        if not self._hwnd:
            return
        rect = ctypes.wintypes.RECT()
        user32.GetClientRect(self._container_hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 0 and h > 0:
            user32.MoveWindow(self._hwnd, 0, 0, w, h, True)

    def resize(self, w: int, h: int):
        if self._hwnd and w > 0 and h > 0:
            user32.MoveWindow(self._hwnd, 0, 0, w, h, True)

    def cd(self, path: str):
        self._cwd = path
        self.terminate()
        # Restart after a short delay
        QTimer.singleShot(200, self._start)

    def focus(self):
        if self._hwnd:
            user32.SetForegroundWindow(self._hwnd)
            user32.SetFocus(self._hwnd)

    def terminate(self):
        if self._hwnd:
            user32.SendMessageW(self._hwnd, WM_CLOSE, 0, 0)
            self._hwnd = None
        if self._hProcess:
            kernel32.WaitForSingleObject(self._hProcess, 3000)
            kernel32.CloseHandle(self._hProcess)
            self._hProcess = None
        if self._hThread:
            kernel32.CloseHandle(self._hThread)
            self._hThread = None

    def hwnd(self):
        return self._hwnd


class NativeTerminalWidget(QFrame):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("terminal-container")
        self._shell = _default_shell()
        self._default_cwd = os.getcwd()
        self._sessions: list[NativeTerminalSession] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar row
        tab_row = QWidget()
        tab_row.setObjectName("terminal-tab-row")
        tab_row.setFixedHeight(28)
        tab_layout = QHBoxLayout(tab_row)
        tab_layout.setContentsMargins(4, 0, 4, 0)
        tab_layout.setSpacing(2)

        self._tab_bar = QTabBar()
        self._tab_bar.setObjectName("terminal-tab-bar")
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setExpanding(False)
        self._tab_bar.tabCloseRequested.connect(self._close_session)
        self._tab_bar.currentChanged.connect(self._switch_session)
        tab_layout.addWidget(self._tab_bar, 1)

        self._add_btn = QPushButton()
        self._add_btn.setObjectName("terminal-add-btn")
        self._add_btn.setFixedSize(20, 20)
        self._add_btn.setIcon(QIcon())
        self._add_btn.setText("+")
        self._add_btn.clicked.connect(self._add_session)
        tab_layout.addWidget(self._add_btn)

        self._clear_btn = QPushButton()
        self._clear_btn.setObjectName("terminal-clear-btn")
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.setText("C")
        self._clear_btn.setToolTip("Restart terminal")
        self._clear_btn.clicked.connect(self._restart_current)
        tab_layout.addWidget(self._clear_btn)

        self._close_panel_btn = QPushButton()
        self._close_panel_btn.setObjectName("terminal-close-btn")
        self._close_panel_btn.setFixedSize(20, 20)
        self._close_panel_btn.setText("X")
        self._close_panel_btn.setToolTip("Close panel")
        self._close_panel_btn.clicked.connect(lambda: self._set_visible(False))
        tab_layout.addWidget(self._close_panel_btn)

        layout.addWidget(tab_row)

        # Container for embedded terminal windows
        self._container = QWidget()
        self._container.setObjectName("terminal-container")
        self._container.setStyleSheet("background-color: #0a0a0a;")
        layout.addWidget(self._container, 1)

        self._add_session()

    def _add_session(self, cwd=None):
        idx = len(self._sessions)
        tab_name = f"Term {idx + 1}"
        self._tab_bar.addTab(tab_name)
        self._tab_bar.setTabData(idx, str(idx))
        self._tab_bar.setTabsClosable(True)

        session = NativeTerminalSession(
            self._shell, cwd or self._default_cwd,
            int(self._container.winId()),
        )
        self._sessions.append(session)
        self._tab_bar.setCurrentIndex(idx)

        # Resize the new session to fill container
        QTimer.singleShot(500, lambda: self._resize_current())

    def _switch_session(self, idx: int):
        for i, s in enumerate(self._sessions):
            hwnd = s.hwnd()
            if hwnd:
                if i == idx:
                    user32.ShowWindow(hwnd, SW_SHOW)
                    QTimer.singleShot(100, lambda h=hwnd: user32.SetForegroundWindow(h))
                else:
                    user32.ShowWindow(hwnd, SW_HIDE)
        self._resize_current()

    def _close_session(self, idx: int):
        if len(self._sessions) <= 1:
            return
        if 0 <= idx < len(self._sessions):
            self._sessions[idx].terminate()
            del self._sessions[idx]
            self._tab_bar.removeTab(idx)

    def _restart_current(self):
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._sessions):
            self._sessions[idx].cd(self._default_cwd)

    def _resize_current(self):
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._sessions):
            rect = self._container.rect()
            self._sessions[idx].resize(rect.width(), rect.height())

    def _set_visible(self, visible: bool):
        self.setVisible(visible)
        self.toggled.emit(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(50, self._resize_current)

    def focus_input(self):
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._sessions):
            self._sessions[idx].focus()

    def set_workdir(self, path: str):
        self._default_cwd = path
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._sessions):
            self._sessions[idx].cd(path)

    def terminate_all(self):
        for s in self._sessions:
            s.terminate()
        self._sessions.clear()

    def process(self):
        """Compatibility shim for main_window closeEvent."""
        return None

    def cd(self, path: str):
        self.set_workdir(path)
