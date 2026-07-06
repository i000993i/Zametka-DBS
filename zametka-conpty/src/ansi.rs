use pyo3::prelude::*;

/// 8 standard ANSI colors (indices 30-37 / 40-47).
const ANSI_COLORS: &[&str] = &[
    "#000000", "#cc0000", "#4e9a06", "#c4a000",
    "#3465a4", "#75507b", "#06989a", "#d3d7cf",
];

/// Bright ANSI colors (indices 90-97 / 100-107).
const ANSI_BRIGHT: &[&str] = &[
    "#555753", "#ef2929", "#8ae234", "#fce94f",
    "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeee",
];

/// 256-color palette (indices 0-255).
const ANSI_256: &[&str] = &[
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
];

/// A segment of terminal text with its formatting.
#[pyclass]
#[derive(Clone)]
pub struct AnsiSegment {
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub fg: Option<String>,
    #[pyo3(get)]
    pub bg: Option<String>,
    #[pyo3(get)]
    pub bold: bool,
}

/// Parse ANSI escape sequences in `text` and return a list of formatted segments.
///
/// `fg0` — default foreground hex color (e.g. `"#c9d1d9"`)
/// `fg2` — dim foreground hex color (used for background code 100)
#[pyfunction]
#[allow(unused_variables)]
pub fn parse_ansi(text: &str, fg0: &str, fg2: &str) -> Vec<AnsiSegment> {
    let mut segments: Vec<AnsiSegment> = Vec::new();
    let mut current_fg: Option<String> = None;
    let mut current_bg: Option<String> = None;
    let mut current_bold = false;
    let mut seg_buf = String::new();

    let bytes = text.as_bytes();
    let len = bytes.len();
    let mut i = 0;

    macro_rules! flush {
        () => {
            if !seg_buf.is_empty() {
                segments.push(AnsiSegment {
                    text: std::mem::take(&mut seg_buf),
                    fg: current_fg.clone(),
                    bg: current_bg.clone(),
                    bold: current_bold,
                });
            }
        };
    }

    while i < len {
        if bytes[i] != 0x1B {
            let start = i;
            while i < len && bytes[i] != 0x1B {
                i += 1;
            }
            seg_buf.push_str(&text[start..i]);
            continue;
        }

        // Escape sequence starting
        if i + 1 >= len {
            break;
        }

        if bytes[i + 1] == b'[' {
            // CSI: ESC [ params... final(0x40-0x7E)
            let param_start = i + 2;
            let mut j = param_start;
            while j < len && !(0x40..=0x7E).contains(&bytes[j]) {
                j += 1;
            }
            if j < len {
                let final_byte = bytes[j];
                let params = &text[param_start..j];

                if final_byte == b'm' {
                    flush!();
                    apply_sgr(&mut current_fg, &mut current_bg, &mut current_bold, params, fg0, fg2);
                }
                // For J and K — just ignore, handled in Python
                i = j + 1;
            } else {
                i = j;
            }
        } else if bytes[i + 1] == b']' {
            // OSC: ESC ] ... ST (\x07 or ESC \)
            let mut j = i + 2;
            while j < len && bytes[j] != 0x07 {
                if bytes[j] == 0x1B && j + 1 < len && bytes[j + 1] == b'\\' {
                    j += 2;
                    break;
                }
                j += 1;
            }
            if j < len && bytes[j] == 0x07 {
                j += 1;
            }
            i = j;
        } else {
            // Other escape: skip 2
            i += 2;
        }
    }

    flush!();
    segments
}

#[allow(unused_variables)]
fn apply_sgr(
    fg: &mut Option<String>,
    bg: &mut Option<String>,
    bold: &mut bool,
    params: &str,
    fg0: &str,
    fg2: &str,
) {
    let codes: Vec<i32> = if params.is_empty() {
        vec![0]
    } else {
        params
            .split(';')
            .filter_map(|s| s.parse::<i32>().ok())
            .collect()
    };

    let mut ci = 0;
    while ci < codes.len() {
        let c = codes[ci];
        match c {
            0 => {
                *bold = false;
                *fg = None;
                *bg = None;
            }
            1 => *bold = true,
            22 => *bold = false,
            30..=37 => {
                *fg = Some(ANSI_COLORS[(c - 30) as usize].to_string());
            }
            39 => *fg = None,
            40..=47 => {
                *bg = Some(ANSI_COLORS[(c - 40) as usize].to_string());
            }
            49 => *bg = None,
            100 => *bg = Some(fg2.to_string()),
            101..=107 => {
                *bg = Some(ANSI_BRIGHT[(c - 101) as usize].to_string());
            }
            90 => *fg = Some("#808080".to_string()),
            91..=97 => {
                *fg = Some(ANSI_BRIGHT[(c - 91) as usize].to_string());
            }
            38 if ci + 1 < codes.len() => {
                if codes[ci + 1] == 5 && ci + 2 < codes.len() {
                    let idx = codes[ci + 2];
                    if (0..256).contains(&idx) {
                        *fg = Some(ANSI_256[idx as usize].to_string());
                    }
                    ci += 2;
                } else if codes[ci + 1] == 2 && ci + 4 < codes.len() {
                    let r = codes[ci + 2].clamp(0, 255);
                    let g = codes[ci + 3].clamp(0, 255);
                    let b = codes[ci + 4].clamp(0, 255);
                    *fg = Some(format!("#{:02x}{:02x}{:02x}", r, g, b));
                    ci += 4;
                }
                ci += 1;
            }
            48 if ci + 1 < codes.len() => {
                if codes[ci + 1] == 5 && ci + 2 < codes.len() {
                    let idx = codes[ci + 2];
                    if (0..256).contains(&idx) {
                        *bg = Some(ANSI_256[idx as usize].to_string());
                    }
                    ci += 2;
                } else if codes[ci + 1] == 2 && ci + 4 < codes.len() {
                    let r = codes[ci + 2].clamp(0, 255);
                    let g = codes[ci + 3].clamp(0, 255);
                    let b = codes[ci + 4].clamp(0, 255);
                    *bg = Some(format!("#{:02x}{:02x}{:02x}", r, g, b));
                    ci += 4;
                }
                ci += 1;
            }
            _ => {}
        }
        ci += 1;
    }
}
