import ctypes
from ctypes import wintypes

from . import winapi

ENUM_CURRENT_SETTINGS = -1
DM_BITSPERPEL, DM_PELSWIDTH, DM_PELSHEIGHT, DM_DISPLAYFREQUENCY = 0x40000, 0x80000, 0x100000, 0x400000
DM_DISPLAYFIXEDOUTPUT = 0x20000000
DMDFO_STRETCH = 2
CDS_FULLSCREEN = 0x4
DISP_CHANGE_SUCCESSFUL = 0


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD), ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD), ("dmPositionX", wintypes.LONG), ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD), ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD), ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD), ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD),
    ]


def _devmode():
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    return dm


def current_mode():
    if not winapi.IS_WIN:
        return 1920, 1080, 60
    dm = _devmode()
    ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
    return dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency


def list_modes():
    """Unique (w, h) of the primary monitor with their best refresh rate, largest first."""
    if not winapi.IS_WIN:
        return [(1920, 1080, 60), (1680, 1050, 60), (1280, 960, 60), (1024, 768, 60)]
    best = {}
    i = 0
    dm = _devmode()
    while ctypes.windll.user32.EnumDisplaySettingsW(None, i, ctypes.byref(dm)):
        if dm.dmBitsPerPel >= 32 and dm.dmPelsWidth >= 800:
            key = (dm.dmPelsWidth, dm.dmPelsHeight)
            best[key] = max(best.get(key, 0), dm.dmDisplayFrequency)
        i += 1
    return sorted(((w, h, hz) for (w, h), hz in best.items()), key=lambda m: (-m[0] * m[1], -m[0]))


def native_mode():
    modes = list_modes()
    return modes[0] if modes else current_mode()


def pick_mode(aspect, prefer_heights):
    """Supported mode closest to aspect (w/h), preferring the given heights in order."""
    modes = [m for m in list_modes() if abs(m[0] / m[1] - aspect) < 0.02]
    for h in prefer_heights:
        for m in modes:
            if m[1] == h:
                return m
    return modes[0] if modes else None


def set_mode(width, height, hz=0, stretch=True):
    if not winapi.IS_WIN:
        return False
    dm = _devmode()
    ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
    dm.dmPelsWidth, dm.dmPelsHeight = width, height
    dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT
    if hz:
        dm.dmDisplayFrequency = hz
        dm.dmFields |= DM_DISPLAYFREQUENCY
    if stretch:
        dm.dmDisplayFixedOutput = DMDFO_STRETCH
        dm.dmFields |= DM_DISPLAYFIXEDOUTPUT
    res = ctypes.windll.user32.ChangeDisplaySettingsExW(None, ctypes.byref(dm), None, CDS_FULLSCREEN, None)
    if res != DISP_CHANGE_SUCCESSFUL and stretch:
        return set_mode(width, height, hz, stretch=False)
    return res == DISP_CHANGE_SUCCESSFUL


def restore():
    if winapi.IS_WIN:
        ctypes.windll.user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
