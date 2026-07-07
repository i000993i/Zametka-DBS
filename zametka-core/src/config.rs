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
        "language": "ru",
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

fn val_to_py(val: &Value, py: Python<'_>) -> PyObject {
    match val {
        Value::Null => py.None(),
        Value::Bool(b) => b.into_py(py),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                i.into_py(py)
            } else if let Some(f) = n.as_f64() {
                f.into_py(py)
            } else {
                py.None()
            }
        }
        Value::String(s) => s.clone().into_py(py),
        Value::Array(arr) => {
            let items: Vec<PyObject> = arr.iter().map(|v| val_to_py(v, py)).collect();
            items.into_py(py)
        }
        Value::Object(obj) => {
            let dict = pyo3::types::PyDict::new(py);
            for (k, v) in obj {
                dict.set_item(k.as_str(), val_to_py(v, py)).ok();
            }
            dict.into()
        }
    }
}

fn py_to_val(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() {
        Ok(Value::Null)
    } else if let Ok(s) = obj.extract::<String>() {
        Ok(Value::String(s))
    } else if let Ok(b) = obj.extract::<bool>() {
        Ok(Value::Bool(b))
    } else if let Ok(i) = obj.extract::<i64>() {
        Ok(Value::Number(i.into()))
    } else if let Ok(f) = obj.extract::<f64>() {
        Ok(Value::Number(serde_json::Number::from_f64(f).unwrap_or(serde_json::Number::from_f64(0.0).unwrap())))
    } else if let Ok(list) = obj.extract::<Vec<Bound<'_, PyAny>>>() {
        let items: PyResult<Vec<Value>> = list.iter().map(|item| py_to_val(item)).collect();
        Ok(Value::Array(items?))
    } else if let Ok(dict) = obj.downcast::<pyo3::types::PyDict>() {
        let mut map = serde_json::Map::new();
        for (k, v) in dict {
            let key = k.extract::<String>()?;
            map.insert(key, py_to_val(&v)?);
        }
        Ok(Value::Object(map))
    } else {
        Ok(Value::String(obj.to_string()))
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
            match std::fs::read_to_string(&config_file) {
                Ok(content) => {
                    if let Ok(parsed) = serde_json::from_str::<Value>(&content) {
                        merge(&mut data, &parsed);
                    }
                }
                Err(e) => eprintln!("[zametka_core] Failed to read config: {e}"),
            }
        }
        if let Err(e) = std::fs::create_dir_all(&dir) {
            eprintln!("[zametka_core] Failed to create config dir: {e}");
        }
        let cfg = Config { data, path: config_file };
        cfg.save();
        cfg
    }

    pub fn get(&self, key: &str, py: Python<'_>) -> PyObject {
        let keys: Vec<&str> = key.split('.').collect();
        let mut current = &self.data;
        for k in &keys {
            match current.get(*k) {
                Some(v) => current = v,
                None => return py.None(),
            }
        }
        val_to_py(current, py)
    }

    pub fn set(&mut self, key: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let keys: Vec<&str> = key.split('.').collect();
        if keys.is_empty() {
            return Ok(());
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
        current[last] = py_to_val(value)?;
        self.save();
        Ok(())
    }

    fn save(&self) {
        match serde_json::to_string_pretty(&self.data) {
            Ok(content) => {
                if let Err(e) = std::fs::write(&self.path, content) {
                    eprintln!("[zametka_core] Failed to write config: {e}");
                }
            }
            Err(e) => eprintln!("[zametka_core] Failed to serialize config: {e}"),
        }
    }
}
