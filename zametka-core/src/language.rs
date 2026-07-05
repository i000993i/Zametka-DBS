use pyo3::prelude::*;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

static LANGUAGE_INFO: &[(&str, &str, &str)] = &[
    (".py", "Python", "#9d7cd8"),
    (".pyw", "Python", "#9d7cd8"),
    (".js", "JavaScript", "#f0db4f"),
    (".mjs", "JavaScript", "#f0db4f"),
    (".jsx", "JavaScript", "#f0db4f"),
    (".ts", "TypeScript", "#3178c6"),
    (".tsx", "TypeScript", "#3178c6"),
    (".html", "HTML", "#e34f26"),
    (".htm", "HTML", "#e34f26"),
    (".css", "CSS", "#1572b6"),
    (".scss", "CSS", "#1572b6"),
    (".java", "Java", "#b07219"),
    (".c", "C", "#555555"),
    (".cpp", "C++", "#f34b7d"),
    (".h", "C", "#555555"),
    (".hpp", "C++", "#f34b7d"),
    (".cs", "C#", "#178600"),
    (".go", "Go", "#00add8"),
    (".rs", "Rust", "#dea584"),
    (".sql", "SQL", "#e38c00"),
    (".rb", "Ruby", "#701516"),
    (".php", "PHP", "#4f5d95"),
    (".swift", "Swift", "#f05138"),
    (".kt", "Kotlin", "#7f52ff"),
    (".dart", "Dart", "#00d2b8"),
    (".lua", "Lua", "#000080"),
    (".sh", "Shell", "#4eaa25"),
    (".bash", "Shell", "#4eaa25"),
    (".ps1", "PowerShell", "#012456"),
    (".yaml", "YAML", "#cb171e"),
    (".yml", "YAML", "#cb171e"),
    (".toml", "TOML", "#9c4221"),
    (".json", "JSON", "#292929"),
    (".ini", "INI", "#808080"),
    (".md", "Markdown", "#083fa1"),
    (".txt", "Text", "#808080"),
];

#[pyfunction]
pub fn detect_language(filepath: &str) -> Option<(String, String)> {
    let path = Path::new(filepath);
    let ext = path.extension()?.to_string_lossy().to_lowercase();
    let ext_with_dot = format!(".{}", ext);
    for (e, name, color) in LANGUAGE_INFO {
        if *e == ext_with_dot {
            return Some((name.to_string(), color.to_string()));
        }
    }
    None
}

#[pyfunction]
pub fn scan_folder_languages(folder_path: &str, max_depth: usize) -> Vec<(String, String)> {
    let path = Path::new(folder_path);
    if !path.is_dir() {
        return Vec::new();
    }

    let mut ext_count: HashMap<String, usize> = HashMap::new();
    scan_dir(path, 0, max_depth, &mut ext_count);

    // Count unique languages, keep top 5 by frequency
    let mut lang_count: HashMap<String, (String, String, usize)> = HashMap::new();
    for (ext, count) in &ext_count {
        for (e, name, color) in LANGUAGE_INFO {
            if e == &format!(".{}", ext) {
                let entry = lang_count.entry(name.to_string()).or_insert_with(|| {
                    (name.to_string(), color.to_string(), 0)
                });
                entry.2 += count;
                break;
            }
        }
    }

    let mut result: Vec<(String, String, usize)> = lang_count.into_values().collect();
    result.sort_by(|a, b| b.2.cmp(&a.2));
    result.truncate(5);
    result.into_iter().map(|(name, color, _)| (name, color)).collect()
}

fn scan_dir(dir: &Path, depth: usize, max_depth: usize, counts: &mut HashMap<String, usize>) {
    if depth > max_depth {
        return;
    }
    let entries = match fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return,
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
            if name.starts_with('.') || name == "node_modules" || name == "__pycache__" {
                continue;
            }
            scan_dir(&path, depth + 1, max_depth, counts);
        } else if path.is_file() {
            if let Some(ext) = path.extension() {
                let ext_str = ext.to_string_lossy().to_lowercase();
                *counts.entry(ext_str).or_insert(0) += 1;
            }
        }
    }
}
