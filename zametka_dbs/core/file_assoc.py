import os
import sys
import winreg


REG_KEY = r"Software\Classes"
APP_ID = "Zametka"
EXTENSIONS = [".md", ".markdown", ".mdown"]


def register_file_associations(app_path: str = ""):
    if sys.platform != "win32":
        return

    if not app_path:
        app_path = os.path.abspath(sys.argv[0])
    if not app_path.endswith(".exe"):
        app_path = os.path.join(os.path.dirname(app_path), "Zametka.exe")

    exe_dir = os.path.dirname(app_path)

    # In a PyInstaller bundle, assets are in _internal/assets
    ico_path = os.path.join(exe_dir, "assets", "app_icon.ico")
    if not os.path.isfile(ico_path):
        ico_path = os.path.join(exe_dir, "_internal", "assets", "app_icon.ico")
    if not os.path.isfile(ico_path):
        ico_path = ""

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{REG_KEY}\\{APP_ID}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Zametka Note")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{REG_KEY}\\{APP_ID}\\DefaultIcon") as key:
            icon_val = f"{ico_path},0" if ico_path else ""
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_val)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{REG_KEY}\\{APP_ID}\\shell\\open\\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{app_path}" "%1"')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{REG_KEY}\\{APP_ID}\\shell\\open\\drop-target") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{app_path}" "%1"')

        for ext in EXTENSIONS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{REG_KEY}\\{ext}\\OpenWithProgids") as key:
                winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, "")

    except Exception as e:
        print(f"Failed to register file associations: {e}", file=sys.stderr)


def unregister_file_associations():
    if sys.platform != "win32":
        return

    try:
        for ext in EXTENSIONS:
            try:
                key_path = f"{REG_KEY}\\{ext}\\OpenWithProgids"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, APP_ID)
                    except FileNotFoundError:
                        pass
            except FileNotFoundError:
                pass

        def _delete_key_recursive(root, sub_key):
            try:
                with winreg.OpenKey(root, sub_key, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            child = winreg.EnumKey(key, i)
                            _delete_key_recursive(root, f"{sub_key}\\{child}")
                            i = 0
                        except OSError:
                            break
                winreg.DeleteKey(root, sub_key)
            except FileNotFoundError:
                pass

        _delete_key_recursive(winreg.HKEY_CURRENT_USER, f"{REG_KEY}\\{APP_ID}")

    except Exception as e:
        print(f"Failed to unregister file associations: {e}", file=sys.stderr)
