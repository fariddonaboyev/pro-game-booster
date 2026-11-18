import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "PROGameBooster"
FILE = APP_DIR / "settings.json"

DEFAULTS = {
    "crosshair": {
        "style": "Plyus",
        "color": "#00ff00",
        "color_mode": "Moslashuvchan",
        "rainbow_speed": 5,
        "size": 8,
        "thickness": 2,
        "gap": 3,
        "outline": True,
        "dot": False,
        "offset_x": 0,
        "offset_y": 0,
        "opacity": 100,
        "hotkey": "F6",
    },
    "lupa": {
        "zoom": 2.5,
        "size": 260,
        "shape": "Doira",
        "border": True,
        "border_color": "#ffffff",
        "smooth": True,
        "offset_x": 0,
        "offset_y": 0,
        "mode": "Yoqib-o'chirish",
        "hotkey": "F7",
        "zoom_in": "Num +",
        "zoom_out": "Num -",
        "fps": 60,
    },
    "booster": {
        "hotkey": "F8",
        "power_plan": True,
        "trim_ram": True,
        "clean_temp": False,
        "flush_dns": True,
        "game": "cs2.exe",
        "kill": [],
        "prev_power_plan": "",
    },
    "cs2": {
        "hud_scaling": 0.95,
        "radar_hud_scale": 1.3,
        "radar_scale": 0.45,
        "radar_centered": False,
        "viewmodel_fov": 68,
        "fps_max": 0,
        "game_crosshair": "O'zgartirmaslik",
        "stretch": True,
        "restore_hotkey": "F9",
    },
}


def _merge(base, data):
    out = {}
    for key, value in base.items():
        if isinstance(value, dict):
            out[key] = _merge(value, data.get(key, {}) if isinstance(data.get(key), dict) else {})
        else:
            out[key] = data.get(key, value) if isinstance(data, dict) else value
    return out


def load():
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return _merge(DEFAULTS, data)


def save(cfg):
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
