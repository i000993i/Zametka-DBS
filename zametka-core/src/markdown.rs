use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;
use std::sync::LazyLock;

static WIKILINK_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]").unwrap()
});

/// Find all .md files in a vault and return a name→path mapping
/// (same logic as Python LinkResolver._rebuild_index)
#[pyfunction]
pub fn find_markdown_files(vault_path: &str) -> HashMap<String, String> {
    let mut map = HashMap::new();
    let path = std::path::Path::new(vault_path);
    if !path.is_dir() {
        return map;
    }
    walk_md_files(path, vault_path, &mut map);
    map
}

fn walk_md_files(dir: &std::path::Path, vault_root: &str, map: &mut HashMap<String, String>) {
    let entries = match std::fs::read_dir(dir) {
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
            walk_md_files(&path, vault_root, map);
        } else if path.extension().map_or(false, |e| e == "md") {
            let full = path.to_string_lossy().to_string();
            // bare name: "MyNote" -> full path
            let bare = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
            map.entry(bare).or_insert_with(|| full.clone());
            // relative path: "subdir/MyNote" -> full path
            if let Ok(rel) = path.strip_prefix(vault_root) {
                let rel_str = rel.with_extension("").to_string_lossy().to_string().replace('\\', "/");
                map.entry(rel_str).or_insert(full);
            }
        }
    }
}

/// Render Markdown to HTML using comrak
#[pyfunction]
pub fn render_markdown(text: &str) -> String {
    let mut options = comrak::Options::default();
    options.extension.strikethrough = true;
    options.extension.table = true;
    options.extension.tasklist = true;
    options.extension.autolink = true;
    options.render.hardbreaks = false;
    options.parse.smart = true;
    comrak::markdown_to_html(text, &options)
}

/// Resolve [[wikilinks]] in HTML using a name→path dict
#[pyfunction]
pub fn resolve_wikilinks(html: &str, note_map: HashMap<String, String>) -> String {
    let mut result = String::with_capacity(html.len());
    let mut last_end = 0;

    for cap in WIKILINK_RE.find_iter(html) {
        result.push_str(&html[last_end..cap.start()]);
        let inner = &html[cap.start() + 2..cap.end() - 2];
        let (target, display) = if let Some(pipe) = inner.find('|') {
            (&inner[..pipe], &inner[pipe + 1..])
        } else {
            (inner, inner)
        };

        let target = target.trim();
        if let Some(resolved_path) = note_map.get(target)
            .or_else(|| {
                let no_ext = target.strip_suffix(".md").unwrap_or(target);
                note_map.get(no_ext)
            })
            .or_else(|| {
                let lower = target.to_lowercase();
                note_map.iter().find(|(k, _)| k.to_lowercase() == lower).map(|(_, v)| v)
            })
        {
            result.push_str(&format!(
                "<a href=\"wikilink:///{}\" class=\"wikilink\" data-path=\"{}\">{}</a>",
                url_encode(resolved_path),
                html_escape(&resolved_path),
                html_escape(display)
            ));
        } else {
            result.push_str(&format!(
                "<span class=\"wikilink-unresolved\">{}</span>",
                html_escape(display)
            ));
        }
        last_end = cap.end();
    }
    result.push_str(&html[last_end..]);
    result
}

/// Collect all [[wikilink]] targets from markdown text
#[pyfunction]
pub fn extract_wikilinks(text: &str) -> Vec<String> {
    WIKILINK_RE
        .captures_iter(text)
        .map(|cap| cap.get(1).map_or("", |m| m.as_str()).to_string())
        .collect()
}

/// Build backlinks index using a note_map (name→path).
/// Returns dict of target_path -> list of source_paths
#[pyfunction]
pub fn build_backlinks(note_map: HashMap<String, String>) -> HashMap<String, Vec<String>> {
    let mut backlinks: HashMap<String, Vec<String>> = HashMap::new();
    let all_paths: Vec<String> = note_map.values().cloned().collect();

    for note_path in &all_paths {
        let content = match std::fs::read_to_string(note_path) {
            Ok(c) => c,
            Err(_) => continue,
        };
        let targets = extract_wikilinks(&content);
        for target in targets {
            let target = target.trim();
            let resolved = note_map.get(target)
                .or_else(|| {
                    let no_ext = target.strip_suffix(".md").unwrap_or(target);
                    note_map.get(no_ext)
                })
                .or_else(|| {
                    let lower = target.to_lowercase();
                    note_map.iter().find(|(k, _)| k.to_lowercase() == lower).map(|(_, v)| v)
                });
            if let Some(resolved_path) = resolved {
                backlinks.entry(resolved_path.clone()).or_default().push(note_path.clone());
            }
        }
    }
    backlinks
}

fn html_escape(text: &str) -> String {
    text.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn url_encode(text: &str) -> String {
    text.replace('\\', "/")
        .replace(' ', "%20")
        .replace('#', "%23")
        .replace('?', "%3F")
        .replace('%', "%25")
        .replace('&', "%26")
        .replace('=', "%3D")
        .replace('+', "%2B")
        .replace('<', "%3C")
        .replace('>', "%3E")
        .replace('"', "%22")
        .replace('`', "%60")
        .replace('{', "%7B")
        .replace('}', "%7D")
        .replace('|', "%7C")
        .replace('^', "%5E")
        .replace('~', "%7E")
        .replace('[', "%5B")
        .replace(']', "%5D")
}
