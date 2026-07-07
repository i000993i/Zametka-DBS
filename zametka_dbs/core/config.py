import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)

CONFIG_VERSION = 1

_DEFAULTS = {
    "vault_path": "",
    "theme": "dark",
    "language": "ru",
    "editor": {
        "font_family": "Cascadia Code, JetBrains Mono, Consolas",
        "font_size": 14,
        "tab_size": 4,
        "word_wrap": True,
        "show_line_numbers": True,
    },
    "ui": {
        "sidebar_width": 300,
        "preview_width_ratio": 0.45,
    },
    "preview": {
        "enabled": True,
        "auto_render": True,
    },
    "pinned": {
        "items": [],
    },
}

from zametka_dbs.core.rust_bridge import HAS_RUST, RustConfig


class _PyConfig:
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Zametka")
        self._path = os.path.join(config_dir, "config.json")
        self._data = {}
        self._load()

    @staticmethod
    def _merge_defaults(data: dict) -> dict:
        result = {}
        for k, v in _DEFAULTS.items():
            if isinstance(v, dict):
                result[k] = {**v, **(data.get(k, {}))}
            else:
                result[k] = data.get(k, v)
        for k, v in data.items():
            if k not in _DEFAULTS:
                result[k] = v
        return result

    def _load(self):
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
                self._data = {}
        else:
            self._data = {}
        self._data = self._merge_defaults(self._data)
        self._migrate()

    def _migrate(self):
        current = self._data.get("_config_version", 0)
        if current >= CONFIG_VERSION:
            return
        self._data["_config_version"] = CONFIG_VERSION
        if current < 1:
            self._migrate_v1()
        self._save()

    def _migrate_v1(self):
        old_path = os.path.join(os.environ.get("APPDATA", ""), "Zametka", "config.json")
        new_path = os.path.join(os.environ.get("APPDATA", ""), "Zametka")
        signal_path = os.path.join(new_path, "config.json")
        if old_path != signal_path and os.path.isfile(old_path):
            try:
                shutil.copy2(old_path, signal_path)
                logger.info("Config migrated from legacy location")
            except Exception as e:
                logger.warning(f"Config migration failed: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")

    def get(self, key, default=None):
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def set(self, key, value):
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self._save()


class Config:
    def __init__(self, config_dir=None):
        if HAS_RUST:
            self._inner = RustConfig(config_dir)
        else:
            logger.info("Using Python config backend")
            self._inner = _PyConfig(config_dir)

    def get(self, key, default=None):
        if HAS_RUST:
            val = self._inner.get(key)
            if val is None:
                return default
            return val
        val = self._inner.get(key, None)
        if val is None:
            return default
        return val

    def set(self, key, value):
        self._inner.set(key, value)


_config_instance = None


def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
