use pyo3::prelude::*;

#[pyfunction]
fn compute_line_numbers(text: &str) -> Vec<(u32, String)> {
    let mut result = Vec::new();
    let mut display: u32 = 0;
    for line in text.split('\n') {
        let trimmed = line.trim();
        let is_blank = trimmed.is_empty();
        if !is_blank {
            display += 1;
        }
        let typ = if is_blank {
            "blank"
        } else if trimmed.starts_with("```") {
            "code"
        } else if trimmed.starts_with('#') {
            "heading"
        } else if trimmed.starts_with("- ") || trimmed.starts_with("* ") || trimmed.starts_with("+ ") {
            "list"
        } else {
            "normal"
        };
        result.push((display, typ.to_string()));
    }
    result
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_line_numbers, m)?)?;
    Ok(())
}
