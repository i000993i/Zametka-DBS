/// dbs-renderer — render document pages via PyMuPDF subprocess.
use std::env;
use std::fs;
use std::io::{self, Write};
use std::process::{Command, Stdio};

const PYTHON: &str = r"C:\Users\m6280\Desktop\OtherProject\files\rapota\testing\Zametka-DBS\.venv\Scripts\python.exe";

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: dbs-renderer <file> <page> [dpi] [--output <file>]");
        std::process::exit(1);
    }
    let file = &args[1];
    let page: usize = args[2].parse().expect("page must be integer");
    let dpi: f32 = args.get(3).and_then(|s| s.parse().ok()).unwrap_or(150.0);
    let output = args.iter().position(|a| a == "--output").and_then(|p| args.get(p + 1).cloned());

    let script = format!(
        "import sys, fitz\n\
         doc = fitz.open(r'{file}')\n\
         page = doc[{page}]\n\
         zoom = {dpi} / 72.0\n\
         pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)\n\
         w, h = pix.width, pix.height\n\
         sys.stdout.buffer.write(f'DATA {{w}} {{h}}\\n'.encode())\n\
         sys.stdout.buffer.write(pix.samples)\n"
    );

    let result = Command::new(PYTHON)
        .arg("-c")
        .arg(&script)
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .and_then(|c| c.wait_with_output());

    match result {
        Ok(out) => {
            let raw = &out.stdout;
            if raw.starts_with(b"ERROR ") {
                let text = String::from_utf8_lossy(&raw[6..]);
                eprintln!("Render error: {text}");
                std::process::exit(1);
            }
            if !raw.starts_with(b"DATA ") {
                let text = String::from_utf8_lossy(raw);
                eprintln!("Unexpected output: {text}");
                std::process::exit(1);
            }
            let newline = raw[5..].iter().position(|&b| b == b'\n')
                .expect("missing newline after DATA");
            let header = &raw[5..5 + newline];
            let hdr = String::from_utf8_lossy(header);
            let mut dims = hdr.split_whitespace();
            let w: i32 = dims.next().unwrap().parse().unwrap();
            let h: i32 = dims.next().unwrap().parse().unwrap();
            let data = &raw[5 + newline + 1..];

            if let Some(path) = output {
                let mut buf = Vec::with_capacity(data.len() + 64);
                let _ = write!(buf, "{w} {h}\n");
                buf.extend_from_slice(data);
                fs::write(&path, &buf).expect("failed to write output file");
            } else {
                let stdout = io::stdout();
                let mut out = stdout.lock();
                let _ = write!(out, "DATA {w} {h}\n");
                let _ = out.write_all(data);
                let _ = out.flush();
            }
        }
        Err(e) => {
            eprintln!("Failed to spawn python: {e}");
            std::process::exit(1);
        }
    }
}
