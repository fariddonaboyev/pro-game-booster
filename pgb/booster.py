import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

from . import winapi

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

PROTECTED = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "lsaiso.exe", "svchost.exe", "explorer.exe", "dwm.exe", "fontdrvhost.exe",
    "sihost.exe", "ctfmon.exe", "conhost.exe", "runtimebroker.exe", "audiodg.exe", "taskhostw.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe", "securityhealthservice.exe",
    "msmpeng.exe", "nissrv.exe", "memcompression", "spoolsv.exe", "wudfhost.exe", "dllhost.exe",
    "searchindexer.exe", "applicationframehost.exe", "lockapp.exe", "userinit.exe", "smartscreen.exe",
    "steam.exe", "steamwebhelper.exe", "steamservice.exe", "cs2.exe", "nvcontainer.exe", "nvdisplay.container.exe",
    "amdrsserv.exe", "atieclxx.exe", "atiesrxx.exe", "rtkaudusvc64.exe", "python.exe", "pythonw.exe",
    "progamebooster.exe",
}

SUGGESTED = {
    "onedrive.exe", "teams.exe", "ms-teams.exe", "skype.exe", "phoneexperiencehost.exe", "yourphone.exe",
    "widgets.exe", "cortana.exe", "googledrivefs.exe", "dropbox.exe", "adobeupdateservice.exe",
    "acrotray.exe", "ccleaner64.exe", "epicgameslauncher.exe", "origin.exe", "eadesktop.exe",
    "battle.net.exe", "ubisoftconnect.exe", "upc.exe", "utorrent.exe", "qbittorrent.exe", "bittorrent.exe",
    "msedge.exe", "opera.exe", "yandex.exe", "browser.exe",
}


def _run(args):
    try:
        return subprocess.run(
            args, check=False, capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _me():
    try:
        return psutil.Process().username()
    except psutil.Error:
        return None


def list_processes():
    """User processes grouped by name: [(name, total_mb, [pids])], biggest first."""
    me, own = _me(), os.getpid()
    groups = {}
    for p in psutil.process_iter(["pid", "name", "username", "memory_info"]):
        info = p.info
        name = (info.get("name") or "").lower()
        if not name or info["pid"] in (0, 4, own) or name in PROTECTED:
            continue
        if me and info.get("username") and info["username"] != me:
            continue
        mem = info.get("memory_info")
        entry = groups.setdefault(name, [0.0, []])
        entry[0] += (mem.rss if mem else 0) / 1048576
        entry[1].append(info["pid"])
    return sorted(((n, mb, pids) for n, (mb, pids) in groups.items()), key=lambda x: -x[1])


def kill_names(names):
    names = {n.lower() for n in names} - PROTECTED
    victims = [p for p in psutil.process_iter(["name"]) if (p.info.get("name") or "").lower() in names]
    for p in victims:
        try:
            p.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(victims, timeout=3)
    for p in alive:
        try:
            p.kill()
        except psutil.Error:
            pass
    return len(victims)


def trim_ram():
    if not winapi.IS_WIN:
        return 0
    access = 0x0100 | 0x0400  # PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION
    count = 0
    for p in psutil.process_iter(["pid"]):
        h = winapi.kernel32.OpenProcess(access, False, p.info["pid"])
        if h:
            if winapi.psapi.EmptyWorkingSet(h):
                count += 1
            winapi.kernel32.CloseHandle(h)
    return count


def active_power_plan():
    m = re.search(r"([0-9a-fA-F-]{36})", _run(["powercfg", "/getactivescheme"]))
    return m.group(1).lower() if m else ""


def set_max_performance():
    prev = active_power_plan()
    _run(["powercfg", "/setactive", HIGH_PERF])
    return prev


def restore_power_plan(guid):
    if guid:
        _run(["powercfg", "/setactive", guid])


def clean_temp():
    freed = 0
    cutoff = time.time() - 3600
    for root in {os.environ.get("TEMP"), os.environ.get("TMP")} - {None}:
        for entry in Path(root).iterdir() if Path(root).is_dir() else []:
            try:
                st = entry.stat()
                if st.st_mtime > cutoff:
                    continue
                if entry.is_dir() and not entry.is_symlink():
                    size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
                    shutil.rmtree(entry)
                else:
                    size = st.st_size
                    entry.unlink()
                freed += size
            except OSError:
                continue
    return freed / 1048576


def flush_dns():
    _run(["ipconfig", "/flushdns"])


def boost_game(exe_name):
    """Raise priority of the running game; returns number of processes changed."""
    exe_name = exe_name.strip().lower()
    if not exe_name:
        return 0
    high = getattr(psutil, "HIGH_PRIORITY_CLASS", -10)
    n = 0
    for p in psutil.process_iter(["name"]):
        if (p.info.get("name") or "").lower() == exe_name:
            try:
                p.nice(high)
                n += 1
            except psutil.Error:
                pass
    return n


def ram_used_mb():
    return psutil.virtual_memory().used / 1048576
