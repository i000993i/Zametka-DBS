use std::ffi::c_void;
use std::os::raw::c_ushort;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};

use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;

type HANDLE = *mut c_void;
type BOOL = i32;
type DWORD = u32;
type HRESULT = i32;
type LPVOID = *mut c_void;
type LPCVOID = *const c_void;
type LPCWSTR = *const u16;
type LPWSTR = *mut u16;
type LPDWORD = *mut DWORD;

const FALSE: BOOL = 0;
const INVALID_HANDLE_VALUE: HANDLE = -1isize as HANDLE;
const PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE: usize = 0x00020016;
const EXTENDED_STARTUPINFO_PRESENT: DWORD = 0x00080000;
const ERROR_BROKEN_PIPE: DWORD = 109;
const STILL_ACTIVE: DWORD = 259;

#[derive(Clone, Copy)]
struct SafeHandle(HANDLE);
unsafe impl Send for SafeHandle {}
unsafe impl Sync for SafeHandle {}

fn h(h: SafeHandle) -> HANDLE { h.0 }
fn safe(h: HANDLE) -> SafeHandle { SafeHandle(h) }

#[repr(C)]
#[derive(Clone, Copy)]
struct COORD { x: c_ushort, y: c_ushort }

#[repr(C)]
struct SECURITY_ATTRIBUTES {
    n_length: DWORD,
    lp_security_descriptor: LPVOID,
    b_inherit_handle: BOOL,
}

#[repr(C)]
struct STARTUPINFOW {
    cb: DWORD, lp_reserved: LPWSTR, lp_desktop: LPWSTR, lp_title: LPWSTR,
    dw_x: DWORD, dw_y: DWORD, dw_x_size: DWORD, dw_y_size: DWORD,
    dw_x_count_chars: DWORD, dw_y_count_chars: DWORD, dw_fill_attribute: DWORD,
    dw_flags: DWORD, w_show_window: u16, cb_reserved2: u16,
    lp_reserved2: *mut u8, h_std_input: HANDLE, h_std_output: HANDLE,
    h_std_error: HANDLE,
}

#[repr(C)]
struct STARTUPINFOEXW {
    startup_info: STARTUPINFOW,
    lp_attribute_list: LPVOID,
}

#[repr(C)]
struct PROCESS_INFORMATION {
    h_process: HANDLE, h_thread: HANDLE,
    dw_process_id: DWORD, dw_thread_id: DWORD,
}

extern "system" {
    fn CreatePseudoConsole(size: COORD, h_input: HANDLE, h_output: HANDLE, dw_flags: DWORD, ph_pc: *mut HANDLE) -> HRESULT;
    fn ClosePseudoConsole(h_pc: HANDLE);
    fn ResizePseudoConsole(h_pc: HANDLE, size: COORD) -> HRESULT;
    fn CreatePipe(ph_read: *mut HANDLE, ph_write: *mut HANDLE, attr: *const SECURITY_ATTRIBUTES, size: DWORD) -> BOOL;
    fn CloseHandle(h: HANDLE) -> BOOL;
    fn ReadFile(file: HANDLE, buf: LPVOID, to_read: DWORD, read: LPDWORD, olap: *mut c_void) -> BOOL;
    fn WriteFile(file: HANDLE, buf: LPCVOID, to_write: DWORD, written: LPDWORD, olap: *mut c_void) -> BOOL;
    fn CreateEventW(attr: *const SECURITY_ATTRIBUTES, manual: BOOL, initial: BOOL, name: LPCWSTR) -> HANDLE;
    fn SetEvent(h: HANDLE) -> BOOL;
    fn ResetEvent(h: HANDLE) -> BOOL;
    fn GetOverlappedResult(file: HANDLE, olap: *mut c_void, xfer: LPDWORD, wait: BOOL) -> BOOL;
    fn WaitForSingleObject(h: HANDLE, ms: DWORD) -> DWORD;
    fn GetExitCodeProcess(proc: HANDLE, code: LPDWORD) -> BOOL;
    fn CreateProcessW(app: LPCWSTR, cmd: LPWSTR, proc_attr: *const SECURITY_ATTRIBUTES, thread_attr: *const SECURITY_ATTRIBUTES, inherit: BOOL, flags: DWORD, env: LPVOID, dir: LPCWSTR, si: *const STARTUPINFOW, pi: *mut PROCESS_INFORMATION) -> BOOL;
    fn InitializeProcThreadAttributeList(list: LPVOID, count: DWORD, flags: DWORD, size: *mut usize) -> BOOL;
    fn UpdateProcThreadAttribute(list: LPVOID, flags: DWORD, attr: usize, value: LPVOID, size: usize, prev: LPVOID, ret_size: *mut usize) -> BOOL;
    fn DeleteProcThreadAttributeList(list: LPVOID) -> BOOL;
    fn GetLastError() -> DWORD;
}

fn to_wchars(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(Some(0)).collect()
}

fn win32_err(msg: &str) -> PyErr {
    let code = unsafe { GetLastError() };
    PyOSError::new_err(format!("{} (Win32 error {})", msg, code))
}

struct Inner {
    buffer: Mutex<Vec<u8>>,
    h_output_read: SafeHandle,
    h_input_write: SafeHandle,
    h_pc: SafeHandle,
    h_process: SafeHandle,
    read_event: SafeHandle,
    running: AtomicBool,
    thread: Mutex<Option<JoinHandle<()>>>,
}

unsafe impl Send for Inner {}
unsafe impl Sync for Inner {}

impl Drop for Inner {
    fn drop(&mut self) {
        self.running.store(false, Ordering::Relaxed);
        unsafe {
            if self.read_event.0 != INVALID_HANDLE_VALUE && !self.read_event.0.is_null() {
                SetEvent(self.read_event.0);
            }
        }
        if let Ok(mut t) = self.thread.lock() {
            if let Some(h) = t.take() {
                let _ = h.join();
            }
        }
        unsafe {
            for &sh in &[self.h_input_write, self.h_output_read, self.read_event] {
                if sh.0 != INVALID_HANDLE_VALUE && !sh.0.is_null() {
                    CloseHandle(sh.0);
                }
            }
            if self.h_process.0 != INVALID_HANDLE_VALUE && !self.h_process.0.is_null() {
                let _ = WaitForSingleObject(self.h_process.0, 5000);
                CloseHandle(self.h_process.0);
            }
        }
    }
}

#[pyclass]
pub struct ConPtyProcess {
    inner: Option<Arc<Inner>>,
}

#[pymethods]
impl ConPtyProcess {
    #[new]
    pub fn new() -> Self {
        ConPtyProcess { inner: None }
    }

    pub fn start(&mut self, shell: &str, cwd: &str, cols: u16, rows: u16) -> PyResult<()> {
        // Use NULL security attributes (non-inheritable pipes) like EchoCon C sample
        let mut h_conpty_input = INVALID_HANDLE_VALUE;
        let mut h_app_input_write = INVALID_HANDLE_VALUE;
        if unsafe { CreatePipe(&mut h_conpty_input, &mut h_app_input_write, std::ptr::null(), 0) } == FALSE {
            return Err(win32_err("CreatePipe input"));
        }

        let mut h_app_output_read = INVALID_HANDLE_VALUE;
        let mut h_conpty_output = INVALID_HANDLE_VALUE;
        if unsafe { CreatePipe(&mut h_app_output_read, &mut h_conpty_output, std::ptr::null(), 0) } == FALSE {
            unsafe { CloseHandle(h_app_input_write); }
            return Err(win32_err("CreatePipe output"));
        }

        let size = COORD { x: cols as c_ushort, y: rows as c_ushort };
        let mut h_pc = INVALID_HANDLE_VALUE;
        let hr = unsafe { CreatePseudoConsole(size, h_conpty_input, h_conpty_output, 0, &mut h_pc) };
        if hr < 0 {
            unsafe { CloseHandle(h_app_input_write); CloseHandle(h_app_output_read); }
            return Err(PyOSError::new_err(format!("CreatePseudoConsole failed: {:08x}", hr)));
        }

        // Close ConPTY-side handles (duped into ConHost per MSDN)
        unsafe { CloseHandle(h_conpty_input); CloseHandle(h_conpty_output); }

        let read_event = unsafe { CreateEventW(std::ptr::null(), 1, 0, std::ptr::null()) };
        if read_event.is_null() || read_event == INVALID_HANDLE_VALUE {
            unsafe { ClosePseudoConsole(h_pc); CloseHandle(h_app_input_write); CloseHandle(h_app_output_read); }
            return Err(win32_err("CreateEventW failed"));
        }

        let mut si = STARTUPINFOEXW {
            startup_info: STARTUPINFOW {
                cb: std::mem::size_of::<STARTUPINFOEXW>() as DWORD,
                lp_reserved: std::ptr::null_mut(), lp_desktop: std::ptr::null_mut(),
                lp_title: std::ptr::null_mut(), dw_x: 0, dw_y: 0,
                dw_x_size: 0, dw_y_size: 0, dw_x_count_chars: 0,
                dw_y_count_chars: 0, dw_fill_attribute: 0, dw_flags: 0,
                w_show_window: 0, cb_reserved2: 0, lp_reserved2: std::ptr::null_mut(),
                h_std_input: std::ptr::null_mut(), h_std_output: std::ptr::null_mut(),
                h_std_error: std::ptr::null_mut(),
            },
            lp_attribute_list: std::ptr::null_mut(),
        };

        let mut attr_size: usize = 0;
        unsafe { InitializeProcThreadAttributeList(std::ptr::null_mut(), 1, 0, &mut attr_size); }
        let mut attr_list: Vec<u8> = vec![0u8; attr_size];
        if unsafe { InitializeProcThreadAttributeList(attr_list.as_mut_ptr() as LPVOID, 1, 0, &mut attr_size) } == FALSE {
            unsafe { ClosePseudoConsole(h_pc); CloseHandle(h_app_input_write); CloseHandle(h_app_output_read); CloseHandle(read_event); }
            return Err(win32_err("InitializeProcThreadAttributeList failed"));
        }
        si.lp_attribute_list = attr_list.as_mut_ptr() as LPVOID;

        if unsafe { UpdateProcThreadAttribute(si.lp_attribute_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE, h_pc as LPVOID, std::mem::size_of::<HANDLE>(), std::ptr::null_mut(), std::ptr::null_mut()) } == FALSE {
            unsafe { DeleteProcThreadAttributeList(si.lp_attribute_list); ClosePseudoConsole(h_pc); CloseHandle(h_app_input_write); CloseHandle(h_app_output_read); CloseHandle(read_event); }
            return Err(win32_err("UpdateProcThreadAttribute failed"));
        }

        let mut cmd = to_wchars(shell);
        let cwd_buf = if cwd.is_empty() { vec![] } else { to_wchars(cwd) };
        let cwd16 = if cwd_buf.is_empty() { std::ptr::null() } else { cwd_buf.as_ptr() };
        let mut pi = PROCESS_INFORMATION {
            h_process: std::ptr::null_mut(), h_thread: std::ptr::null_mut(),
            dw_process_id: 0, dw_thread_id: 0,
        };

        let ret = unsafe { CreateProcessW(
            std::ptr::null(), cmd.as_mut_ptr(),
            std::ptr::null(), std::ptr::null(), FALSE,
            EXTENDED_STARTUPINFO_PRESENT,
            std::ptr::null_mut(), cwd16,
            &si.startup_info as *const STARTUPINFOW, &mut pi,
        ) };
        unsafe { DeleteProcThreadAttributeList(si.lp_attribute_list); }

        if ret == FALSE {
            unsafe { ClosePseudoConsole(h_pc); CloseHandle(h_app_input_write); CloseHandle(h_app_output_read); CloseHandle(read_event); }
            return Err(win32_err(&format!("CreateProcessW failed for {}", shell)));
        }

        // Pipes are non-inheritable (NULL security attributes), no SetHandleInformation needed

        let inner = Arc::new(Inner {
            buffer: Mutex::new(Vec::new()),
            h_output_read: safe(h_app_output_read),
            h_input_write: safe(h_app_input_write),
            h_pc: safe(h_pc),
            h_process: safe(pi.h_process),
            read_event: safe(read_event),
            running: AtomicBool::new(true),
            thread: Mutex::new(None),
        });

        let inner_clone = inner.clone();
        let handle = thread::Builder::new()
            .name("conpty-reader".into())
            .spawn(move || reader_thread(inner_clone))
            .map_err(|e| PyOSError::new_err(format!("Thread spawn: {}", e)))?;

        *inner.thread.lock().unwrap() = Some(handle);
        self.inner = Some(inner);
        Ok(())
    }

    pub fn write(&self, data: &[u8]) -> PyResult<()> {
        let inner = self.inner.as_ref().ok_or_else(|| PyOSError::new_err("Not started"))?;
        if inner.h_input_write.0.is_null() || inner.h_input_write.0 == INVALID_HANDLE_VALUE {
            return Ok(());
        }
        let mut written: DWORD = 0;
        let ret = unsafe { WriteFile(h(inner.h_input_write), data.as_ptr() as LPCVOID, data.len() as DWORD, &mut written, std::ptr::null_mut()) };
        if ret == FALSE {
            let err = unsafe { GetLastError() };
            if err != ERROR_BROKEN_PIPE {
                return Err(win32_err("Write failed"));
            }
        }
        Ok(())
    }

    pub fn read(&mut self) -> Vec<u8> {
        let inner = match self.inner.as_ref() {
            Some(i) => i,
            None => return Vec::new(),
        };
        let mut buf = inner.buffer.lock().unwrap();
        if buf.is_empty() { return Vec::new(); }
        let data = buf.clone();
        buf.clear();
        data
    }

    pub fn resize(&self, cols: u16, rows: u16) -> PyResult<()> {
        let inner = self.inner.as_ref().ok_or_else(|| PyOSError::new_err("Not started"))?;
        if inner.h_pc.0.is_null() || inner.h_pc.0 == INVALID_HANDLE_VALUE {
            return Ok(());
        }
        let size = COORD { x: cols as c_ushort, y: rows as c_ushort };
        let hr = unsafe { ResizePseudoConsole(h(inner.h_pc), size) };
        if hr < 0 { return Err(PyOSError::new_err(format!("Resize: {:08x}", hr))); }
        Ok(())
    }

    pub fn close(&mut self) {
        if let Some(inner) = self.inner.take() {
            inner.running.store(false, Ordering::Relaxed);
            unsafe {
                if inner.read_event.0 != INVALID_HANDLE_VALUE && !inner.read_event.0.is_null() {
                    SetEvent(inner.read_event.0);
                }
                if inner.h_pc.0 != INVALID_HANDLE_VALUE && !inner.h_pc.0.is_null() {
                    ClosePseudoConsole(inner.h_pc.0);
                }
            }
            if let Ok(mut t) = inner.thread.lock() {
                if let Some(h) = t.take() {
                    let _ = Python::with_gil(|py| py.allow_threads(|| h.join()));
                }
            }
        }
    }

    pub fn is_running(&self) -> bool {
        let inner = match self.inner.as_ref() {
            Some(i) => i, None => return false,
        };
        if inner.h_process.0.is_null() || inner.h_process.0 == INVALID_HANDLE_VALUE {
            return false;
        }
        let mut code: DWORD = 0;
        unsafe { GetExitCodeProcess(h(inner.h_process), &mut code); }
        code == STILL_ACTIVE
    }
}

const ERROR_IO_PENDING: DWORD = 997;
const WAIT_OBJECT_0: DWORD = 0;

#[repr(C)]
struct OVERLAPPED {
    internal: usize,
    internal_high: usize,
    offset: DWORD,
    offset_high: DWORD,
    h_event: HANDLE,
}

fn reader_thread(inner: Arc<Inner>) {
    let mut buf = vec![0u8; 65536];

    while inner.running.load(Ordering::Relaxed) {
        let mut nread: DWORD = 0;
        let mut olap = OVERLAPPED { internal: 0, internal_high: 0, offset: 0, offset_high: 0, h_event: h(inner.read_event) };
        unsafe { ResetEvent(h(inner.read_event)); }
        let ret = unsafe { ReadFile(h(inner.h_output_read), buf.as_mut_ptr() as LPVOID, buf.len() as DWORD, &mut nread, &mut olap as *mut OVERLAPPED as *mut c_void) };

        if ret == FALSE {
            let err = unsafe { GetLastError() };
            if err == ERROR_IO_PENDING {
                loop {
                    let wr = unsafe { WaitForSingleObject(h(inner.read_event), 100) };
                    if !inner.running.load(Ordering::Relaxed) { break; }
                    if wr == WAIT_OBJECT_0 {
                        let mut xfer: DWORD = 0;
                        if unsafe { GetOverlappedResult(h(inner.h_output_read), &mut olap as *mut OVERLAPPED as *mut c_void, &mut xfer, FALSE) } != FALSE && xfer > 0 {
                            inner.buffer.lock().unwrap().extend_from_slice(&buf[..xfer as usize]);
                        }
                        break;
                    }
                }
            } else if err == ERROR_BROKEN_PIPE {
                break;
            }
        } else if nread > 0 {
            inner.buffer.lock().unwrap().extend_from_slice(&buf[..nread as usize]);
        }
    }

    inner.running.store(false, Ordering::Relaxed);
}
