import ctypes
import ctypes.wintypes
import logging
import os
import threading
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)

kernel32 = ctypes.windll.kernel32
HRESULT = ctypes.c_long

# COORD
class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

# SECURITY_ATTRIBUTES
class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]

# OVERLAPPED
class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", wintypes.ULONG),
        ("InternalHigh", wintypes.ULONG),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]

# STARTUPINFOW
class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

# STARTUPINFOEXW
class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", wintypes.LPVOID),
    ]

# PROCESS_INFORMATION
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

# Constants
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
PROC_THREAD_ATTRIBUTE_INPUT = 0x00020000  # ProcThreadAttributeValue(0, FALSE, TRUE, FALSE)
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
ERROR_IO_PENDING = 997
ERROR_BROKEN_PIPE = 109
WAIT_OBJECT_0 = 0
INFINITE = 0xFFFFFFFF

# Resolve function signatures
kernel32.CreatePipe.restype = wintypes.BOOL
kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(SECURITY_ATTRIBUTES),
    wintypes.DWORD,
]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

kernel32.CreatePseudoConsole.restype = HRESULT
kernel32.CreatePseudoConsole.argtypes = [
    COORD,
    wintypes.HANDLE,
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
]

kernel32.ClosePseudoConsole.restype = None
kernel32.ClosePseudoConsole.argtypes = [wintypes.HANDLE]

kernel32.ResizePseudoConsole.restype = HRESULT
kernel32.ResizePseudoConsole.argtypes = [wintypes.HANDLE, COORD]

kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [
    ctypes.POINTER(SECURITY_ATTRIBUTES),
    wintypes.BOOL,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]

kernel32.ReadFile.restype = wintypes.BOOL
kernel32.ReadFile.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED),
]

kernel32.WriteFile.restype = wintypes.BOOL
kernel32.WriteFile.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED),
]

kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

kernel32.GetOverlappedResult.restype = wintypes.BOOL
kernel32.GetOverlappedResult.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(OVERLAPPED),
    ctypes.POINTER(wintypes.DWORD),
    wintypes.BOOL,
]

kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]

CREATE_NO_WINDOW = 0x08000000

# InitializeProcThreadAttributeList / UpdateProcThreadAttribute
# Extract from kernel32 via GetProcAddress since they're in kernel32.dll
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
kernel32.InitializeProcThreadAttributeList.argtypes = [
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_size_t),
]

kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
kernel32.UpdateProcThreadAttribute.argtypes = [
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.c_size_t,  # DWORD_PTR
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.LPVOID,
    ctypes.POINTER(ctypes.c_size_t),
]

kernel32.DeleteProcThreadAttributeList.restype = wintypes.BOOL
kernel32.DeleteProcThreadAttributeList.argtypes = [wintypes.LPVOID]

# CreateProcessW
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.POINTER(SECURITY_ATTRIBUTES),
    ctypes.POINTER(SECURITY_ATTRIBUTES),
    wintypes.BOOL,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW),
    ctypes.POINTER(PROCESS_INFORMATION),
]

kernel32.SetHandleInformation.restype = wintypes.BOOL
kernel32.SetHandleInformation.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.DWORD,
]

HANDLE_FLAG_INHERIT = 1


class ConPtyProcess:
    def __init__(self):
        self._hPC = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        self._hProcess = wintypes.HANDLE(None)
        self._hThread = wintypes.HANDLE(None)
        self._hOutputRead = wintypes.HANDLE(None)
        self._hInputWrite = wintypes.HANDLE(None)
        self._read_event = wintypes.HANDLE(None)
        self._read_overlapped = None
        self._output_thread = None
        self._running = False
        self._on_output_cb = None
        self._on_exit_cb = None
        self._shutdown = threading.Event()

    def start(
        self,
        shell: str,
        cwd: str,
        cols: int = 80,
        rows: int = 25,
        on_output=None,
        on_exit=None,
    ):
        self._on_output_cb = on_output
        self._on_exit_cb = on_exit

        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(sa)
        sa.bInheritHandle = True
        sa.lpSecurityDescriptor = None

        # Create input pipe: app writes → ConPTY reads
        hConPtyInput = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        hAppInputWrite = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        ret = kernel32.CreatePipe(
            ctypes.byref(hConPtyInput),
            ctypes.byref(hAppInputWrite),
            ctypes.byref(sa),
            0,
        )
        if not ret:
            raise OSError("CreatePipe failed for input pipe")
        self._hInputWrite = hAppInputWrite

        # Create output pipe: ConPTY writes → app reads
        hAppOutputRead = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        hConPtyOutput = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        ret = kernel32.CreatePipe(
            ctypes.byref(hAppOutputRead),
            ctypes.byref(hConPtyOutput),
            ctypes.byref(sa),
            0,
        )
        if not ret:
            kernel32.CloseHandle(self._hInputWrite)
            self._hInputWrite = wintypes.HANDLE(None)
            raise OSError("CreatePipe failed for output pipe")
        self._hOutputRead = hAppOutputRead

        # Create pseudo console
        size = COORD(cols, rows)
        hPC = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        ret = kernel32.CreatePseudoConsole(
            size, hConPtyInput, hConPtyOutput, 0, ctypes.byref(hPC)
        )
        if not ret or ret < 0:
            kernel32.CloseHandle(self._hInputWrite)
            kernel32.CloseHandle(self._hOutputRead)
            self._hInputWrite = wintypes.HANDLE(None)
            self._hOutputRead = wintypes.HANDLE(None)
            raise OSError(f"CreatePseudoConsole failed (HRESULT: {ret:08x})")

        self._hPC = hPC

        # Close the ConPTY-side pipe handles (owned by ConPTY now)
        kernel32.CloseHandle(hConPtyInput)
        kernel32.CloseHandle(hConPtyOutput)

        # Create read event for overlapped I/O
        self._read_event = kernel32.CreateEventW(None, True, False, None)
        if not self._read_event:
            self.close()
            raise OSError("CreateEventW failed")

        self._read_overlapped = OVERLAPPED()
        self._read_overlapped.hEvent = self._read_event

        # Prepare startup info
        si = STARTUPINFOEXW()
        si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)

        # Allocate attribute list
        attr_size = ctypes.c_size_t(0)
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
        attr_list = ctypes.create_string_buffer(attr_size.value)
        ret = kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, ctypes.byref(attr_size))
        if not ret:
            self.close()
            raise OSError("InitializeProcThreadAttributeList failed")
        si.lpAttributeList = ctypes.cast(attr_list, wintypes.LPVOID)

        # Set PSEUDOCONSOLE attribute
        hpc_val = ctypes.c_void_p(self._hPC.value)
        ret = kernel32.UpdateProcThreadAttribute(
            si.lpAttributeList,
            0,
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            ctypes.byref(hpc_val),
            ctypes.sizeof(wintypes.HANDLE),
            None,
            None,
        )
        if not ret:
            kernel32.DeleteProcThreadAttributeList(si.lpAttributeList)
            self.close()
            raise OSError("UpdateProcThreadAttribute failed")

        # Build command line (shell + no arguments for interactive mode)
        cmd = ctypes.create_unicode_buffer(shell)

        pi = PROCESS_INFORMATION()
        ret = kernel32.CreateProcessW(
            None,
            cmd,
            None,
            None,
            False,
            EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
            None,
            cwd if cwd else None,
            ctypes.byref(si.StartupInfo),
            ctypes.byref(pi),
        )

        # Clean up attribute list regardless
        kernel32.DeleteProcThreadAttributeList(si.lpAttributeList)

        if not ret:
            self.close()
            raise OSError(f"CreateProcessW failed for {shell}")

        self._hProcess = pi.hProcess
        self._hThread = pi.hThread

        # Set pipe handles to non-inheritable (they belong only to our process)
        self._set_handle_no_inherit(self._hInputWrite)
        self._set_handle_no_inherit(self._hOutputRead)

        self._running = True
        self._output_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._output_thread.start()

    def _set_handle_no_inherit(self, handle):
        if handle and handle.value:
            ret = kernel32.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0)
            if not ret:
                logger.warning("SetHandleInformation failed")

    def write(self, data: bytes):
        if not self._hInputWrite or self._hInputWrite.value is None:
            return
        written = wintypes.DWORD(0)
        ret = kernel32.WriteFile(
            self._hInputWrite,
            data,
            len(data),
            ctypes.byref(written),
            None,
        )
        if not ret:
            err = ctypes.GetLastError()
            if err != ERROR_BROKEN_PIPE:
                logger.warning(f"ConPTY write failed: error {err}")

    def resize(self, cols: int, rows: int):
        if self._hPC and self._hPC.value and self._hPC.value != INVALID_HANDLE_VALUE:
            size = COORD(cols, rows)
            ret = kernel32.ResizePseudoConsole(self._hPC, size)
            if ret < 0:
                logger.warning(f"ResizePseudoConsole failed: {ret:08x}")

    def close(self):
        self._shutdown.set()
        self._running = False

        # Close pseudo console first — breaks the output pipe and unblocks ReadFile
        if self._hPC and self._hPC.value and self._hPC.value != INVALID_HANDLE_VALUE:
            kernel32.ClosePseudoConsole(self._hPC)
            self._hPC = wintypes.HANDLE(INVALID_HANDLE_VALUE)

        # Wait for the read thread to finish
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=2.0)

        # Now safe to close remaining handles
        handles = [
            ("_hInputWrite", self._hInputWrite),
            ("_hOutputRead", self._hOutputRead),
        ]
        for name, h in handles:
            if h and h.value and h.value != INVALID_HANDLE_VALUE:
                kernel32.CloseHandle(h)
                setattr(self, name, wintypes.HANDLE(None))

        if self._read_event and self._read_event.value and self._read_event.value != INVALID_HANDLE_VALUE:
            kernel32.CloseHandle(self._read_event)
            self._read_event = wintypes.HANDLE(None)

        if self._hProcess and self._hProcess.value:
            kernel32.WaitForSingleObject(self._hProcess, 5000)
            kernel32.CloseHandle(self._hProcess)
            self._hProcess = wintypes.HANDLE(None)

        if self._hThread and self._hThread.value:
            kernel32.CloseHandle(self._hThread)
            self._hThread = wintypes.HANDLE(None)

    def is_running(self) -> bool:
        if not self._hProcess or not self._hProcess.value:
            return False
        exit_code = wintypes.DWORD(0)
        kernel32.GetExitCodeProcess(self._hProcess, ctypes.byref(exit_code))
        return exit_code.value == 259  # STILL_ACTIVE

    def _read_loop(self):
        buf = ctypes.create_string_buffer(4096)
        error_count = 0
        while self._running and not self._shutdown.is_set():
            nread = wintypes.DWORD(0)
            ret = kernel32.ReadFile(
                self._hOutputRead,
                buf,
                ctypes.sizeof(buf),
                ctypes.byref(nread),
                self._read_overlapped,
            )
            if not ret:
                err = ctypes.GetLastError()
                if err == ERROR_IO_PENDING:
                    # Wait for data with timeout so shutdown check works
                    wr = kernel32.WaitForSingleObject(self._read_event, 200)
                    if self._shutdown.is_set():
                        break
                    if wr == WAIT_OBJECT_0:
                        ret = kernel32.GetOverlappedResult(
                            self._hOutputRead,
                            self._read_overlapped,
                            ctypes.byref(nread),
                            False,
                        )
                        if not ret:
                            error_count += 1
                            if error_count > 10:
                                break
                            kernel32.ResetEvent(self._read_event)
                            continue
                        error_count = 0
                        if nread.value > 0 and self._on_output_cb:
                            self._on_output_cb(buf.raw[: nread.value])
                        kernel32.ResetEvent(self._read_event)
                    continue
                elif err == ERROR_BROKEN_PIPE:
                    break
                else:
                    error_count += 1
                    if error_count > 10:
                        break
                    continue
            else:
                error_count = 0
                # Synchronous completion
                if nread.value > 0 and self._on_output_cb:
                    self._on_output_cb(buf.raw[: nread.value])

        if self._on_exit_cb:
            self._on_exit_cb()
