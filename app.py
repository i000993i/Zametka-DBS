import sys
import os
import logging
import traceback

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from zametka_dbs.core.event_bus import get_bus
from zametka_dbs.core.config import get_config
from zametka_dbs.ui.main_window import MainWindow


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("markdown_it").setLevel(logging.WARNING)
    logging.getLogger("zametka_dbs.core.event_bus").setLevel(logging.WARNING)
    logging.getLogger("zametka_dbs.core.config").setLevel(logging.INFO)
    logging.getLogger("zametka_dbs.search.engine").setLevel(logging.INFO)


def _crash_log(exc_info):
    """Write crash to file so user can find it after restart."""
    try:
        path = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "Zametka", "crash.log"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            traceback.print_exception(*exc_info, file=f)
            f.write("\n")
    except Exception:
        pass


def _show_error_dialog(title, message):
    """Show an error dialog, creating QApplication if needed."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.critical(None, title, message)


def excepthook(exc_type, exc_value, exc_tb):
    """Global hook: log crash, show dialog, then exit."""
    _crash_log((exc_type, exc_value, exc_tb))
    _show_error_dialog(
        "Zametka — Unexpected Error",
        f"{exc_type.__name__}: {exc_value}\n\n"
        f"A crash log was saved to %APPDATA%\\Zametka\\crash.log",
    )
    sys.exit(1)


sys.excepthook = excepthook


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    if "--unregister" in sys.argv:
        from zametka_dbs.core.file_assoc import unregister_file_associations
        unregister_file_associations()
        print("File associations removed.")
        return

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Zametka")
        app.setOrganizationName("Zametka")

        ico = os.path.join(os.path.dirname(__file__), "assets", "app_icon.ico")
        if os.path.isfile(ico):
            app.setWindowIcon(QIcon(ico))

        config = get_config()
        logger.info(f"Config loaded. Vault: {config.get('vault_path') or '(none)'}")

        window = MainWindow()
        window.show()
        window.raise_()
        window.activateWindow()

        register_on_startup()

        # Open file passed as command-line argument (e.g., from Explorer)
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: window.open_file(args[0]))

        sys.exit(app.exec())
    except Exception:
        exc_info = sys.exc_info()
        _crash_log(exc_info)
        _show_error_dialog(
            "Zametka — Startup Error",
            traceback.format_exc(),
        )
        sys.exit(1)


def register_on_startup():
    try:
        exe = os.path.abspath(sys.executable)
        if exe.endswith(("python.exe", "pythonw.exe")):
            exe = ""
        from zametka_dbs.core.file_assoc import register_file_associations
        register_file_associations(exe)
    except Exception as e:
        logging.getLogger(__name__).warning(f"File assoc registration: {e}")


if __name__ == "__main__":
    main()
