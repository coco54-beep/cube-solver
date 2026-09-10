"""用户偏好持久化（浅层 key-value，JSON 文件）。

集中管理 ~/.cubesolver_prefs.json，避免各模块各自覆写整个文件而互相冲掉
彼此的键（历史上主题保存会覆盖同文件里的其他偏好）。
"""

import json
import os

_PREFS_FILE = os.path.join(os.path.expanduser("~"), ".cubesolver_prefs.json")


def load() -> dict:
    """读取全部偏好；文件缺失/损坏时返回空 dict。"""
    try:
        with open(_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value):  # noqa: A001 - 语义即「设置偏好」
    """合并写入单个偏好键，保留文件中其他键。"""
    data = load()
    data[key] = value
    try:
        with open(_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
