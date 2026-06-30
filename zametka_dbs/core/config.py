import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    from zametka_core import Config as RustConfig

    class Config:
        def __init__(self, config_dir=None):
            self._inner = RustConfig(config_dir)

        def get(self, key, default=None):
            val = self._inner.get(key, None)
            if val == "" and default is not None:
                return default
            keys = key.split(".")
            last = keys[-1]
            if last in ("enabled", "word_wrap", "show_line_numbers", "auto_render"):
                if val == "":
                    return default if default is not None else False
                return val.lower() == "true"
            if last in ("font_size", "tab_size", "sidebar_width", "max_results"):
                if val == "":
                    return default if default is not None else 0
                try:
                    return int(float(val))
                except ValueError:
                    return default
            if last in ("preview_width_ratio", "line_height"):
                if val == "":
                    return default if default is not None else 0.0
                try:
                    return float(val)
                except ValueError:
                    return default
            if isinstance(default, list):
                if val and val.startswith("["):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        pass
                return default if default is not None else []
            return val if val != "" else (default if default is not None else "")

        def set(self, key, value):
            self._inner.set(key, str(value))

    _config_instance = None

    def get_config():
        global _config_instance
        if _config_instance is None:
            _config_instance = Config()
        return _config_instance

except ImportError:
    logger.info("Rust core not available, using Python config")

    DEFAULT_CONFIG = {
        "vault_path": "",
        "theme": "dark",
        "editor": {
            "font_family": "Cascadia Code, JetBrains Mono, Consolas",
            "font_size": 14,
            "line_height": 1.6,
            "tab_size": 4,
            "word_wrap": True,
            "show_line_numbers": True,
        },
        "ui": {
            "font_family": "Segoe UI Variable Display, Segoe UI",
            "font_size": 13,
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
        "plugins": {
            "enabled": [],
        },
    }

    class Config:
        def __init__(self, config_dir=None):
            if config_dir is None:
                config_dir = self._default_config_dir()
            self._config_dir = Path(config_dir)
            self._config_file = self._config_dir / "config.json"
            self._data = dict(DEFAULT_CONFIG)
            self._load()

        def _default_config_dir(self):
            if os.name == "nt":
                base = os.environ.get("APPDATA", os.path.expanduser("~"))
                return str(Path(base) / "Zametka")
            return str(Path.home() / ".config" / "zametka")

        def _load(self):
            self._config_dir.mkdir(parents=True, exist_ok=True)
            if self._config_file.exists():
                try:
                    with open(self._config_file, "r", encoding="utf-8") as f:
                        self._data = {**DEFAULT_CONFIG, **json.load(f)}
                    logger.info(f"Config loaded from {self._config_file}")
                except Exception as e:
                    logger.warning(f"Failed to load config: {e}, using defaults")
                    self._save()
            else:
                logger.info("No config file found, creating with defaults")
                self._save()

        def _save(self):
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)

        def get(self, key, default=None):
            keys = key.split(".")
            value = self._data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value

        def set(self, key, value):
            keys = key.split(".")
            target = self._data
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value
            self._save()

        @property
        def data(self):
            return self._data

    _config_instance = None

    def get_config():
        global _config_instance
        if _config_instance is None:
            _config_instance = Config()
        return _config_instance
