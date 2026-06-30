import sys
import os
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from zametka_dbs.core.event_bus import get_bus, Events
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


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    if "--unregister" in sys.argv:
        from zametka_dbs.core.file_assoc import unregister_file_associations
        unregister_file_associations()
        print("File associations removed.")
        return

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
    sys.exit(app.exec())


def register_on_startup():
    try:
        exe = os.path.abspath(sys.executable)
        if exe.endswith("python.exe") or exe.endswith("pythonw.exe"):
            script = os.path.abspath(__file__)
            exe = f'"{exe}" "{script}"'
        from zametka_dbs.core.file_assoc import register_file_associations
        register_file_associations(exe if exe.startswith('"') else exe)
    except Exception as e:
        logging.getLogger(__name__).warning(f"File assoc registration: {e}")


if __name__ == "__main__":
    main()
