import re
import sys
from pathlib import Path

CFG_REL = Path("steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg")
BEGIN, END = "// >>> PRO Game Booster", "// <<< PRO Game Booster"
LAUNCH_OPTIONS = "+exec autoexec"
GAME_CROSSHAIR = ["O'zgartirmaslik", "Yashirish (overlay ishlatganda)"]

PRESETS = {
    "Keng (maksimal ko'rish)": {
        "aspect": 16 / 9, "heights": [], "stretch": False,
        "info": "16:9 — eng keng gorizontal ko'rinish, qurol ekran chetiga surilgan.",
        "cfg": {"viewmodel_fov": 68, "viewmodel_offset_x": 2.5, "viewmodel_offset_y": 0,
                "viewmodel_offset_z": -1.5},
    },
    "O'rtacha (16:10)": {
        "aspect": 16 / 10, "heights": [1050, 900, 1200, 800], "stretch": True,
        "info": "16:10 — kenglik va kattalik o'rtasi.",
        "cfg": {"viewmodel_fov": 68, "viewmodel_offset_x": 2, "viewmodel_offset_y": 0,
                "viewmodel_offset_z": -1.5},
    },
    "Tor (4:3 cho'zilgan)": {
        "aspect": 4 / 3, "heights": [960, 1080, 768, 1024], "stretch": True,
        "info": "4:3 cho'zilgan — ko'rinish torroq, lekin dushmanlar kattaroq (kichik monitorga qulay).",
        "cfg": {"viewmodel_fov": 68, "viewmodel_offset_x": 2.5, "viewmodel_offset_y": 0,
                "viewmodel_offset_z": -1.5},
    },
}


def steam_dir():
    if sys.platform != "win32":
        return None
    import winreg

    for hive, key, value in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
    ):
        try:
            with winreg.OpenKey(hive, key) as k:
                return Path(winreg.QueryValueEx(k, value)[0])
        except OSError:
            continue
    return None


def library_dirs(steam):
    libs = [steam]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    try:
        for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore")):
            libs.append(Path(m.group(1).replace("\\\\", "\\")))
    except OSError:
        pass
    return libs


def find_cfg_dir():
    steam = steam_dir()
    candidates = library_dirs(steam) if steam else []
    candidates += [Path(f"{d}:/SteamLibrary") for d in "CDEFG"]
    candidates += [Path(f"{d}:/Program Files (x86)/Steam") for d in "CD"]
    for lib in candidates:
        cfg = lib / CFG_REL
        if cfg.is_dir():
            return cfg
    return None


def build_cfg(cs2, preset_cfg=None):
    lines = [
        f"hud_scaling {float(cs2['hud_scaling']):.2f}",
        f"cl_hud_radar_scale {float(cs2['radar_hud_scale']):.2f}",
        f"cl_radar_scale {float(cs2['radar_scale']):.2f}",
        f"cl_radar_always_centered {int(bool(cs2['radar_centered']))}",
        f"viewmodel_fov {int(cs2['viewmodel_fov'])}",
        f"fps_max {int(cs2['fps_max'])}",
    ]
    for key, value in (preset_cfg or {}).items():
        if key != "viewmodel_fov":
            lines.append(f"{key} {value}")
    if cs2.get("game_crosshair", "").startswith("Yashirish"):
        lines.append("cl_crosshairalpha 0")
        lines.append("cl_crosshair_drawoutline 0")
    return "\n".join([BEGIN, *lines, 'echo "PRO Game Booster cfg yuklandi"', END])


def write_autoexec(cfg_dir, block):
    path = Path(cfg_dir) / "autoexec.cfg"
    try:
        old = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        old = ""
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    new = pattern.sub(lambda _m: block, old) if pattern.search(old) else (old.rstrip() + "\n\n" + block).lstrip()
    path.write_text(new + "\n", encoding="utf-8")
    return path
