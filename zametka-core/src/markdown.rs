use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;
use std::sync::LazyLock;

static WIKILINK_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]").unwrap()
});

static HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(#{1,6})\s+(.+)$").unwrap()
});

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

/// Resolve [[wikilinks]] in HTML: replace unresolved links with clickable spans
#[pyfunction]
pub fn resolve_wikilinks(html: &str, known_notes: Vec<String>) -> String {
    let known: Vec<&str> = known_notes.iter().map(|s| s.as_str()).collect();
    let mut result = String::with_capacity(html.len());
    let mut last_end = 0;

    for cap in WIKILINK_RE.find_iter(html) {
        result.push_str(&html[last_end..cap.start()]);
        let inner = &html[cap.start() + 2..cap.end() - 2]; // strip [[ and ]]
        let (target, display) = if let Some(pipe) = inner.find('|') {
            (&inner[..pipe], &inner[pipe + 1..])
        } else {
            (inner, inner)
        };

        let resolved = resolve_note_path(target, &known);
        match resolved {
            Some(resolved_path) => {
                    result.push_str(&format!(
                        "<a href=\"#\" class=\"wikilink\" data-path=\"{}\">{}</a>",
                        resolved_path.replace('\\', "\\\\").replace('"', "&quot;"),
                        html_escape(display)
                    ));
            }
            None => {
                result.push_str(&format!(
                    "<span class=\"wikilink-unresolved\">{}</span>",
                    html_escape(display)
                ));
            }
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

/// Build backlinks index: returns dict of note_path -> list of backlink sources
#[pyfunction]
pub fn build_backlinks(all_notes: Vec<String>) -> HashMap<String, Vec<String>> {
    let mut backlinks: HashMap<String, Vec<String>> = HashMap::new();
    for note_path in &all_notes {
        let content = match std::fs::read_to_string(note_path) {
            Ok(c) => c,
            Err(_) => continue,
        };
        let targets = extract_wikilinks(&content);
        for target in targets {
            let notes_refs: Vec<&str> = all_notes.iter().map(|s| s.as_str()).collect();
            if let Some(resolved) = resolve_note_path(&target, &notes_refs) {
                backlinks.entry(resolved.to_string()).or_default().push(note_path.clone());
            }
        }
    }
    backlinks
}

/// Generate a table of contents from markdown headings
#[pyfunction]
pub fn table_of_contents(text: &str) -> Vec<(usize, String, String)> {
    let mut toc = Vec::new();
    for line in text.lines() {
        if let Some(cap) = HEADING_RE.captures(line) {
            let level = cap.get(1).map_or(0, |m| m.as_str().len());
            let heading_text = cap.get(2).map_or("", |m| m.as_str()).trim().to_string();
            let anchor = heading_text
                .to_lowercase()
                .chars()
                .filter(|c| c.is_alphanumeric() || *c == ' ' || *c == '-')
                .collect::<String>()
                .replace(' ', "-");
            if !heading_text.is_empty() {
                toc.push((level, anchor, heading_text));
            }
        }
    }
    toc
}

fn resolve_note_path<'a>(target: &str, known_notes: &[&'a str]) -> Option<&'a str> {
    // Try exact match first
    for note in known_notes {
        let name = note.rsplit(std::path::MAIN_SEPARATOR).next()
            .or_else(|| note.rsplit('/').next())
            .unwrap_or(note);
        let name_no_ext = name.strip_suffix(".md").unwrap_or(name);
        if name_no_ext == target || name == target {
            return Some(note);
        }
    }
    // Try case-insensitive
    let target_lower = target.to_lowercase();
    for note in known_notes {
        let name = note.rsplit(std::path::MAIN_SEPARATOR).next()
            .or_else(|| note.rsplit('/').next())
            .unwrap_or(note);
        let name_no_ext = name.strip_suffix(".md").unwrap_or(name);
        if name_no_ext.to_lowercase() == target_lower || name.to_lowercase() == target_lower {
            return Some(note);
        }
    }
    None
}

fn html_escape(text: &str) -> String {
    text.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}
