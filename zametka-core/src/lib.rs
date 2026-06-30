mod config;
mod markdown;
mod search;
mod language;

use pyo3::prelude::*;

#[pymodule]
fn zametka_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Config
    m.add_class::<config::Config>()?;

    // Search
    m.add_class::<search::SearchIndex>()?;

    // Markdown
    m.add_function(wrap_pyfunction!(markdown::render_markdown, m)?)?;
    m.add_function(wrap_pyfunction!(markdown::resolve_wikilinks, m)?)?;
    m.add_function(wrap_pyfunction!(markdown::extract_wikilinks, m)?)?;
    m.add_function(wrap_pyfunction!(markdown::build_backlinks, m)?)?;
    m.add_function(wrap_pyfunction!(markdown::table_of_contents, m)?)?;

    // Language
    m.add_function(wrap_pyfunction!(language::detect_language, m)?)?;
    m.add_function(wrap_pyfunction!(language::scan_folder_languages, m)?)?;

    Ok(())
}
