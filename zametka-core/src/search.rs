use pyo3::prelude::*;
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use unicode_segmentation::UnicodeSegmentation;

#[pyclass]
pub struct SearchIndex {
    files: Vec<String>,
    index: HashMap<String, Vec<(usize, f64)>>,  // term -> [(file_idx, tf_idf)]
    num_docs: usize,
}

#[pymethods]
impl SearchIndex {
    #[new]
    pub fn new() -> Self {
        SearchIndex {
            files: Vec::new(),
            index: HashMap::new(),
            num_docs: 0,
        }
    }

    pub fn index_file(&mut self, path: &str, content: &str) {
        let file_idx = self.files.len();
        self.files.push(path.to_string());
        self.num_docs += 1;

        let terms = self.tokenize(content);
        let mut tf: HashMap<String, usize> = HashMap::new();
        let total_terms = terms.len() as f64;
        for t in terms {
            *tf.entry(t).or_insert(0) += 1;
        }

        for (term, count) in tf {
            let tf_val = (count as f64) / total_terms;
            let entry = self.index.entry(term).or_default();
            entry.push((file_idx, tf_val));
        }
    }

    pub fn index_vault(&mut self, vault_path: &str) -> PyResult<usize> {
        let path = Path::new(vault_path);
        if !path.is_dir() {
            return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                "Vault path not found",
            ));
        }
        let mut count = 0;
        self.walk_and_index(path, &mut count)?;
        Ok(count)
    }

    pub fn search(&self, query: &str, max_results: usize) -> Vec<(String, f64)> {
        let terms = self.tokenize(query);
        if terms.is_empty() || self.num_docs == 0 {
            return Vec::new();
        }

        let idf: HashMap<String, f64> = terms
            .iter()
            .map(|t| {
                let df = self.index.get(t).map_or(0, |v| v.len());
                let idf = if df > 0 {
                    (self.num_docs as f64 / df as f64).ln() + 1.0
                } else {
                    0.0
                };
                (t.clone(), idf)
            })
            .collect();

        let mut scores: HashMap<usize, f64> = HashMap::new();
        for term in &terms {
            if let Some(idf_val) = idf.get(term) {
                if *idf_val == 0.0 {
                    continue;
                }
                if let Some(postings) = self.index.get(term) {
                    for (file_idx, tf_val) in postings {
                        *scores.entry(*file_idx).or_insert(0.0) += tf_val * idf_val;
                    }
                }
            }
        }

        let mut results: Vec<(usize, f64)> = scores.into_iter().collect();
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(max_results);

        results
            .into_iter()
            .map(|(idx, score)| (self.files[idx].clone(), score))
            .collect()
    }

    pub fn clear(&mut self) {
        self.files.clear();
        self.index.clear();
        self.num_docs = 0;
    }
}

impl SearchIndex {
    fn tokenize(&self, text: &str) -> Vec<String> {
        text.unicode_words()
            .map(|w| w.to_lowercase())
            .filter(|w| w.len() > 1)
            .collect()
    }

    fn walk_and_index(&mut self, dir: &Path, count: &mut usize) -> PyResult<()> {
        let entries = fs::read_dir(dir).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read dir: {}", e))
        })?;
        for entry in entries {
            let entry = entry.map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read entry: {}", e))
            })?;
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
                if name.starts_with('.') || name == "node_modules" || name == "__pycache__" {
                    continue;
                }
                self.walk_and_index(&path, count)?;
            } else if path.is_file() {
                let ext = path.extension().unwrap_or_default().to_string_lossy().to_lowercase();
                let text_exts = [
                    "md", "txt", "py", "js", "ts", "html", "css", "rs", "go", "java",
                    "c", "cpp", "h", "cs", "rb", "php", "swift", "kt", "dart", "lua",
                    "sh", "ps1", "yaml", "yml", "toml", "json", "ini", "cfg", "conf",
                    "sql", "r", "scala", "zig", "nim", "ex", "exs",
                ];
                if !text_exts.contains(&ext.as_str()) {
                    continue;
                }
                if let Ok(content) = fs::read_to_string(&path) {
                    let path_str = path.to_string_lossy().to_string();
                    self.index_file(&path_str, &content);
                    *count += 1;
                }
            }
        }
        Ok(())
    }
}
