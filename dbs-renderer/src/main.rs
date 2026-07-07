use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::Path;

use ab_glyph::{FontArc, PxScale, Font};
use image::{RgbaImage, Rgba};
use image::imageops;

fn load_font() -> Result<FontArc, String> {
    let candidates = [
        // Windows
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cour.ttf",    // Courier New
        r"C:\Windows\Fonts\lucon.ttf",   // Lucida Console
        r"C:\Windows\Fonts\arial.ttf",
        // Cross-platform fallbacks
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ];
    for path in &candidates {
        if let Ok(data) = fs::read(path) {
            if let Ok(font) = FontArc::try_from_vec(data) {
                return Ok(font);
            }
        }
    }
    Err("no system font found".into())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: dbs-renderer <file> <page> [dpi] [--output <file>]");
        std::process::exit(1);
    }
    let file = &args[1];
    let page: usize = args[2].parse().expect("page must be integer");
    let dpi: f32 = args.get(3).and_then(|s| s.parse().ok()).unwrap_or(150.0);
    let output = args.iter().position(|a| a == "--output").and_then(|p| args.get(p + 1));

    match render_page(file, page, dpi) {
        Ok((w, h, data)) => {
            if let Some(path) = output {
                let mut buf = Vec::with_capacity(data.len() + 64);
                let _ = write!(buf, "{w} {h}\n");
                buf.extend_from_slice(&data);
                fs::write(path, &buf).expect("failed to write output file");
            } else {
                let stdout = io::stdout();
                let mut out = stdout.lock();
                let _ = write!(out, "DATA {w} {h}\n");
                let _ = out.write_all(&data);
                let _ = out.flush();
            }
        }
        Err(e) => {
            eprintln!("ERROR {e}");
            std::process::exit(1);
        }
    }
}

fn render_page(file: &str, page: usize, dpi: f32) -> Result<(u32, u32, Vec<u8>), String> {
    let path = Path::new(file);
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();

    let text = match ext.as_str() {
        "pdf" => extract_pdf_text(file)?,
        "txt" => fs::read_to_string(file).map_err(|e| format!("read txt: {e}"))?,
        _ => return Err(format!("unsupported format: .{ext}")),
    };

    let lines: Vec<&str> = text.lines().collect();
    let lines_per_page = estimate_lines_per_page(dpi);
    let start = page * lines_per_page;
    let end = (start + lines_per_page).min(lines.len());

    if start >= lines.len() {
        return Err(format!("page {page} out of range ({})", lines.len()));
    }

    let page_text = lines[start..end].join("\n");
    let pt_size = dpi / 12.0;
    render_text_to_rgba(&page_text, pt_size, dpi)
}

fn extract_pdf_text(file: &str) -> Result<String, String> {
    let bytes = fs::read(file).map_err(|e| format!("read pdf: {e}"))?;
    pdf_extract::extract_text_from_mem(&bytes)
        .map_err(|e| format!("pdf extract: {e}"))
}

fn estimate_lines_per_page(dpi: f32) -> usize {
    let font_size = dpi / 12.0;
    let line_height = font_size * 1.4;
    let page_height = dpi * 11.0;
    (page_height / line_height).max(1.0) as usize
}

fn render_text_to_rgba(text: &str, pt_size: f32, dpi: f32) -> Result<(u32, u32, Vec<u8>), String> {
    let font = load_font()?;
    let scale = PxScale::from(pt_size);
    let line_height = pt_size * 1.4;

    let page_w = (dpi * 8.5) as usize;
    let page_h = (dpi * 11.0) as usize;
    let margin = (dpi * 0.75) as f32;

    let mut img = RgbaImage::from_pixel(page_w as u32, page_h as u32, Rgba([255, 255, 255, 255]));

    let mut cursor_y = margin;
    for line in text.lines() {
        let mut cursor_x = margin;
        for ch in line.chars() {
            let glyph = ab_glyph::Glyph {
                id: font.glyph_id(ch),
                position: ab_glyph::point(cursor_x, cursor_y + pt_size * 0.8),
                scale,
            };
            if let Some(outline) = font.outline_glyph(glyph) {
                let bounds = outline.px_bounds();
                let gx = bounds.min.x as i64;
                let gy = bounds.min.y as i64;
                let gw = bounds.width() as u32;
                let gh = bounds.height() as u32;
                if gx >= 0 && gy >= 0 && gx + gw as i64 <= page_w as i64 && gy + gh as i64 <= page_h as i64 {
                    let mut glyph_img = RgbaImage::new(gw.max(1), gh.max(1));
                    outline.draw(|gx2, gy2, c| {
                        if gx2 < gw && gy2 < gh {
                            glyph_img.put_pixel(gx2, gy2, Rgba([0, 0, 0, (c * 255.0) as u8]));
                        }
                    });
                    imageops::overlay(&mut img, &glyph_img, gx, gy);
                }
            }
            cursor_x += pt_size;
        }
        cursor_y += line_height;
        if cursor_y + line_height > page_h as f32 {
            break;
        }
    }

    let w = img.width();
    let h = img.height();
    let data = img.into_raw();
    Ok((w, h, data))
}
