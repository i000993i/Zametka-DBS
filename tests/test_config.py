import os
import tempfile
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zametka_dbs.core.config import _PyConfig, CONFIG_VERSION


def test_pyconfig_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _PyConfig(tmp)
        assert cfg.get("nonexistent") is None
        assert cfg.get("nonexistent", "fallback") == "fallback"


def test_pyconfig_set_get():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _PyConfig(tmp)
        cfg.set("theme", "dark")
        assert cfg.get("theme") == "dark"


def test_pyconfig_nested():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _PyConfig(tmp)
        cfg.set("editor.tab_size", 4)
        assert cfg.get("editor.tab_size") == 4
        assert cfg.get("editor.font_size") is None


def test_config_version():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _PyConfig(tmp)
        assert cfg.get("_config_version") == CONFIG_VERSION


def test_pyconfig_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _PyConfig(tmp)
        cfg.set("vault_path", "/test")
        path = cfg._path
    with tempfile.TemporaryDirectory() as tmp:
        cfg2 = _PyConfig(tmp)
        with open(os.path.join(tmp, "config.json"), "w") as f:
            import json
            json.dump({"vault_path": "/test"}, f)
        cfg2 = _PyConfig(tmp)
        assert cfg2.get("vault_path") == "/test"


if __name__ == "__main__":
    test_pyconfig_defaults()
    test_pyconfig_set_get()
    test_pyconfig_nested()
    test_config_version()
    test_pyconfig_persistence()
    print("All config tests passed")
