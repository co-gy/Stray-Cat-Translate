"""路径与用户配置的读写.

打包进应用的 config.json 只是默认值; 用户保存的配置写到系统用户目录,
不会随 PyInstaller 的临时目录一起被删除:
    macOS:   ~/Library/Application Support/流浪猫翻译/config.json
    Windows: %APPDATA%\\流浪猫翻译\\config.json
    其他:    ~/.config/流浪猫翻译/config.json
"""
import json
import os
import sys

APP_NAME = "流浪猫翻译"
CONFIG_FILENAME = "config.json"


def resource_path(relative_path):
    """打包资源路径 (PyInstaller 运行时为只读的 _MEIPASS 临时目录)"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def user_config_path():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_NAME, CONFIG_FILENAME)


def has_user_config():
    return os.path.exists(user_config_path())


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    """读取用户配置; 没有或损坏时退回打包的默认配置"""
    try:
        return read_json(user_config_path())
    except (OSError, json.JSONDecodeError):
        return read_json(resource_path(CONFIG_FILENAME))


def save_config(conf):
    """写入用户配置 (先写临时文件再替换, 避免写一半导致文件损坏)"""
    path = user_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=4)
    os.replace(path + ".tmp", path)
