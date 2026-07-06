use std::ffi::c_void;
use std::ptr;

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


#[repr(C)]
#[derive(Clone, Copy)]
struct COORD { x: u16, y: u16 }

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
    fn CreatePipe(ph_read: *mut HANDLE, ph_write: *mut HANDLE, attr: *const c_void, size: DWORD) -> BOOL;
    fn CloseHandle(h: HANDLE) -> BOOL;
    fn ReadFile(file: HANDLE, buf: LPVOID, to_read: DWORD, read: LPDWORD, olap: *mut c_void) -> BOOL;
    fn WriteFile(file: HANDLE, buf: LPCVOID, to_write: DWORD, written: LPDWORD, olap: *mut c_void) -> BOOL;
    fn GetExitCodeProcess(proc: HANDLE, code: LPDWORD) -> BOOL;
    fn CreateProcessW(app: LPCWSTR, cmd: LPWSTR, proc_attr: *const c_void, thread_attr: *const c_void, inherit: BOOL, flags: DWORD, env: LPVOID, dir: LPCWSTR, si: *const STARTUPINFOW, pi: *mut PROCESS_INFORMATION) -> BOOL;
    fn InitializeProcThreadAttributeList(list: LPVOID, count: DWORD, flags: DWORD, size: *mut usize) -> BOOL;
    fn UpdateProcThreadAttribute(list: LPVOID, flags: DWORD, attr: usize, value: LPVOID, size: usize, prev: LPVOID, ret_size: *mut usize) -> BOOL;
    fn DeleteProcThreadAttributeList(list: LPVOID) -> BOOL;
    fn GetLastError() -> DWORD;
    fn WaitForSingleObject(h: HANDLE, ms: DWORD) -> DWORD;
    fn CreateThread(attr: *const c_void, stack: usize, start: Option<unsafe extern "system" fn(LPVOID) -> DWORD>, param: LPVOID, flags: DWORD, id: *mut DWORD) -> HANDLE;
    fn GetStdHandle(id: DWORD) -> HANDLE;
    fn GetConsoleMode(h: HANDLE, mode: *mut DWORD) -> BOOL;
    fn SetConsoleMode(h: HANDLE, mode: DWORD) -> BOOL;
}

const STD_OUTPUT_HANDLE: DWORD = -11i32 as DWORD;
const ENABLE_VIRTUAL_TERMINAL_PROCESSING: DWORD = 0x0004;

unsafe extern "system" fn reader_thread(lp: LPVOID) -> DWORD {
    let h_out = *(lp as *const HANDLE);
    let h_console = GetStdHandle(STD_OUTPUT_HANDLE);
    let mut buf = [0u8; 512];
    let mut total: DWORD = 0;
    loop {
        let mut nread: DWORD = 0;
        let ret = ReadFile(h_out, buf.as_mut_ptr() as LPVOID, buf.len() as DWORD, &mut nread, std::ptr::null_mut());
        if ret == FALSE {
            eprintln!("[reader] ReadFile returned FALSE, err={}", GetLastError());
            break;
        }
        if nread > 0 {
            total += nread;
            let mut written: DWORD = 0;
            WriteFile(h_console, buf.as_ptr() as LPCVOID, nread, &mut written, std::ptr::null_mut());
        }
        eprintln!("[reader] read {} bytes (total={})", nread, total);
    }
    eprintln!("[reader] exiting, total={}", total);
    0
}

fn main() {
    unsafe {
        // Enable Console VT Processing (EchoCon style)
        let h_console = GetStdHandle(STD_OUTPUT_HANDLE);
        let mut console_mode: DWORD = 0;
        GetConsoleMode(h_console, &mut console_mode);
        SetConsoleMode(h_console, console_mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
        let mut h_conpty_input = INVALID_HANDLE_VALUE;
        let mut h_app_input_write = INVALID_HANDLE_VALUE;
        if CreatePipe(&mut h_conpty_input, &mut h_app_input_write, std::ptr::null(), 0) == FALSE {
            eprintln!("CreatePipe1 failed: {}", GetLastError());
            return;
        }
        eprintln!("h_conpty_input={:p}, h_app_input_write={:p}", h_conpty_input, h_app_input_write);

        let mut h_app_output_read = INVALID_HANDLE_VALUE;
        let mut h_conpty_output = INVALID_HANDLE_VALUE;
        if CreatePipe(&mut h_app_output_read, &mut h_conpty_output, std::ptr::null(), 0) == FALSE {
            eprintln!("CreatePipe2 failed: {}", GetLastError());
            return;
        }
        eprintln!("h_app_output_read={:p}, h_conpty_output={:p}", h_app_output_read, h_conpty_output);

        let size = COORD { x: 80, y: 25 };
        let mut h_pc = INVALID_HANDLE_VALUE;
        let hr = CreatePseudoConsole(size, h_conpty_input, h_conpty_output, 0, &mut h_pc);
        if hr < 0 {
            eprintln!("CreatePseudoConsole failed: {:08x}", hr);
            return;
        }
        eprintln!("HPCON: {:p}", h_pc);

        CloseHandle(h_conpty_input);
        CloseHandle(h_conpty_output);

        let mut attr_size: usize = 0;
        InitializeProcThreadAttributeList(std::ptr::null_mut(), 1, 0, &mut attr_size);
        let mut attr_list: Vec<u8> = vec![0u8; attr_size];
        if InitializeProcThreadAttributeList(attr_list.as_mut_ptr() as LPVOID, 1, 0, &mut attr_size) == FALSE {
            eprintln!("InitAttrList failed: {}", GetLastError());
            return;
        }

        if UpdateProcThreadAttribute(attr_list.as_mut_ptr() as LPVOID, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE, h_pc as LPVOID, std::mem::size_of::<HANDLE>(), std::ptr::null_mut(), std::ptr::null_mut()) == FALSE {
            eprintln!("UpdateProc failed: {}", GetLastError());
            return;
        }

        let mut si = STARTUPINFOEXW {
            startup_info: STARTUPINFOW {
                cb: std::mem::size_of::<STARTUPINFOEXW>() as DWORD,
                ..std::mem::zeroed()
            },
            lp_attribute_list: attr_list.as_mut_ptr() as LPVOID,
        };

        let mut cmd: Vec<u16> = "ping localhost\0".encode_utf16().collect();
        let mut pi = PROCESS_INFORMATION { h_process: std::ptr::null_mut(), h_thread: std::ptr::null_mut(), dw_process_id: 0, dw_thread_id: 0 };

        if CreateProcessW(std::ptr::null(), cmd.as_mut_ptr(), std::ptr::null(), std::ptr::null(), FALSE, EXTENDED_STARTUPINFO_PRESENT, std::ptr::null_mut(), std::ptr::null(), &si.startup_info as *const STARTUPINFOW, &mut pi) == FALSE {
            eprintln!("CreateProcessW failed: {}", GetLastError());
            return;
        }
        eprintln!("PID: {}", pi.dw_process_id);

        DeleteProcThreadAttributeList(attr_list.as_mut_ptr() as LPVOID);

        // Spawn reader thread (EchoCon style: pass pipe handle)
        let mut tid: DWORD = 0;
        let reader = CreateThread(std::ptr::null(), 0, Some(reader_thread), &h_app_output_read as *const _ as LPVOID, 0, &mut tid);

        // Wait on THREAD handle like EchoCon (not process handle)
        WaitForSingleObject(pi.h_thread, 10000);
        let mut exit_code: DWORD = 0;
        GetExitCodeProcess(pi.h_process, &mut exit_code);
        eprintln!("Exit code: {:08x}", exit_code);

        // Allow listener to catch up (EchoCon style)
        std::thread::sleep(std::time::Duration::from_millis(500));

        eprintln!("Calling ClosePseudoConsole...");
        ClosePseudoConsole(h_pc);
        eprintln!("ClosePseudoConsole done");

        WaitForSingleObject(reader, 2000);

        CloseHandle(pi.h_thread);
        CloseHandle(pi.h_process);
        CloseHandle(h_app_input_write);
        CloseHandle(h_app_output_read);
        CloseHandle(reader);
        eprintln!("Done");
    }
}
