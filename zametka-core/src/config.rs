use pyo3::prelude::*;
use serde_json::{Value, json};
use std::path::PathBuf;

fn default_config_dir() -> PathBuf {
    if cfg!(windows) {
        let base = std::env::var("APPDATA")
            .or_else(|_| std::env::var("USERPROFILE"))
            .unwrap_or_else(|_| ".".into());
        PathBuf::from(base).join("Zametka")
    } else {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
        PathBuf::from(home).join(".config").join("zametka")
    }
}

fn defaults() -> Value {
    json!({
        "vault_path": "",
        "theme": "dark",
        "editor": {
            "font_family": "Cascadia Code, JetBrains Mono, Consolas",
            "font_size": 14,
            "tab_size": 4,
            "word_wrap": true,
            "show_line_numbers": true,
        },
        "ui": {
            "sidebar_width": 300,
            "preview_width_ratio": 0.45,
        },
        "preview": {
            "enabled": true,
            "auto_render": true,
        },
        "pinned": {
            "items": [],
        },
    })
}

fn merge(base: &mut Value, override_val: &Value) {
    match (base, override_val) {
        (Value::Object(base_map), Value::Object(override_map)) => {
            for (k, v) in override_map {
                if base_map.contains_key(k) && base_map[k].is_object() && v.is_object() {
                    merge(&mut base_map[k], v);
                } else {
                    base_map.insert(k.clone(), v.clone());
                }
            }
        }
        (base, override_val) => *base = override_val.clone(),
    }
}

#[pyclass(name = "Config")]
#[derive(Clone)]
pub struct Config {
    data: Value,
    path: PathBuf,
}

#[pymethods]
impl Config {
    #[new]
    #[pyo3(signature = (config_dir=None))]
    pub fn new(config_dir: Option<String>) -> Self {
        let dir = config_dir
            .map(PathBuf::from)
            .unwrap_or_else(default_config_dir);
        let config_file = dir.join("config.json");
        let mut data = defaults();
        if config_file.exists() {
            if let Ok(content) = std::fs::read_to_string(&config_file) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&content) {
                    merge(&mut data, &parsed);
                }
            }
        }
        let _ = std::fs::create_dir_all(&dir);
        let cfg = Config { data, path: config_file };
        cfg.save();
        cfg
    }

    #[pyo3(signature = (key, default=None))]
    pub fn get(&self, key: &str, default: Option<&str>) -> String {
        let keys: Vec<&str> = key.split('.').collect();
        let mut current = &self.data;
        for k in &keys {
            match current.get(*k) {
                Some(v) => current = v,
                None => return default.unwrap_or("").to_string(),
            }
        }
        match current {
            Value::String(s) => s.clone(),
            Value::Bool(b) => b.to_string(),
            Value::Number(n) => n.to_string(),
            Value::Array(a) => serde_json::to_string(a).unwrap_or_default(),
            Value::Object(o) => serde_json::to_string(o).unwrap_or_default(),
            Value::Null => default.unwrap_or("").to_string(),
        }
    }

    pub fn set(&mut self, key: &str, value: &str) {
        let keys: Vec<&str> = key.split('.').collect();
        if keys.is_empty() {
            return;
        }
        let mut current = &mut self.data;
        for i in 0..keys.len() - 1 {
            let k = keys[i];
            if !current.is_object() {
                *current = json!({});
            }
            if !current.get(k).map_or(false, |v| v.is_object() || v.is_array()) {
                current[k] = json!({});
            }
            current = current.get_mut(k).unwrap();
        }
        let last = keys[keys.len() - 1];
        if let Ok(n) = value.parse::<f64>() {
            current[last] = json!(n);
        } else if let Ok(b) = value.parse::<bool>() {
            current[last] = json!(b);
        } else {
            current[last] = json!(value);
        }
        self.save();
    }

    fn save(&self) {
        if let Ok(content) = serde_json::to_string_pretty(&self.data) {
            let _ = std::fs::write(&self.path, content);
        }
    }
}
