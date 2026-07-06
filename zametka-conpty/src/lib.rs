use pyo3::prelude::*;

mod conpty;
mod ansi;

#[pymodule]
fn zametka_conpty(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<conpty::ConPtyProcess>()?;
    m.add_function(wrap_pyfunction!(ansi::parse_ansi, m)?)?;
    Ok(())
}
