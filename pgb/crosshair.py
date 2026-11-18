import colorsys
import time
import tkinter as tk

from . import winapi

KEY_COLOR = "#010101"
STYLES = ["Plyus", "Plyus + nuqta", "T-shakl", "Nuqta", "Doira", "Doira + nuqta", "X-shakl"]
COLOR_MODES = ["Moslashuvchan", "Bitta rang", "Kamalak"]
PRESET_COLORS = ["#00ff00", "#00ffff", "#ffff00", "#ff00ff", "#ff0000", "#ffffff", "#ff8800", "#3399ff"]


def _hex(r, g, b):
    return f"#{max(2, round(r * 255)):02x}{round(g * 255):02x}{round(b * 255):02x}"


def contrast_colors(bg):
    """Main + outline color that stand out on background (r, g, b)."""
    r, g, b = bg
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    h, s, _ = colorsys.rgb_to_hsv(r, g, b)
    bright = lum < 0.5
    if s < 0.25:
        main = (1.0, 1.0, 1.0) if bright else (0.0, 0.0, 0.0)
    else:
        main = colorsys.hsv_to_rgb((h + 0.5) % 1.0, 1.0, 1.0 if bright else 0.35)
    outline = (0.0, 0.0, 0.0) if bright else (1.0, 1.0, 1.0)
    return _hex(*main), _hex(*outline)


def current_colors(cfg, now=None, bg=None):
    now = time.monotonic() if now is None else now
    mode = cfg.get("color_mode", "Moslashuvchan")
    speed = max(1, int(cfg.get("rainbow_speed", 5)))
    if mode == "Moslashuvchan" and bg is not None:
        return contrast_colors(bg)
    if mode == "Kamalak":
        return _hex(*colorsys.hsv_to_rgb((now * speed * 0.05) % 1.0, 1.0, 1.0)), "#020202"
    color = cfg["color"]
    if color.lower() == KEY_COLOR:
        color = "#020202"
    return color, "#020202"


class CrosshairOverlay:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.win = None
        self.canvas = None
        self.hwnd = None
        self._color_items = []
        self._outline_items = []
        self._last_colors = None
        self._region = (0, 0, 1, 1)
        self._tick_job = None

    @property
    def visible(self):
        return self.win is not None

    def toggle(self):
        self.hide() if self.visible else self.show()

    def show(self):
        if self.win:
            self.redraw()
            return
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=KEY_COLOR)
        if winapi.IS_WIN:
            self.win.attributes("-transparentcolor", KEY_COLOR)
        self.canvas = tk.Canvas(self.win, bg=KEY_COLOR, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.redraw()
        self.hwnd = winapi.make_overlay(self.win)
        self._tick()

    def hide(self):
        if self._tick_job:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None
        if self.win:
            self.win.destroy()
        self.win = self.canvas = self.hwnd = None

    def lift(self):
        winapi.keep_on_top(self.hwnd)

    def _tick(self):
        if not self.win:
            return
        mode = self.cfg.get("color_mode")
        if mode != "Bitta rang":
            bg = self._sample_bg() if mode == "Moslashuvchan" else None
            main, edge = current_colors(self.cfg, bg=bg)
            if (main, edge) != self._last_colors:
                self._last_colors = (main, edge)
                for item, kind in self._color_items:
                    self.canvas.itemconfigure(item, **{kind: main})
                for item, kind in self._outline_items:
                    self.canvas.itemconfigure(item, **{kind: edge})
            delay = 30
        else:
            delay = 1000
        self.lift()
        self._tick_job = self.root.after(delay, self._tick)

    def _sample_bg(self):
        try:
            return winapi.sample_avg(*self._region)
        except OSError:
            return None

    def redraw(self):
        if not self.win:
            return
        c = self.cfg
        size, th, gap = int(c["size"]), max(1, int(c["thickness"])), int(c["gap"])
        outline = bool(c["outline"])
        style = c["style"]
        extent = size + gap + th + 4
        dim = extent * 2 + 1
        cx = cy = extent
        sw, sh = winapi.screen_size()
        x = sw // 2 - cx + int(c["offset_x"])
        y = sh // 2 - cy + int(c["offset_y"])
        self.win.geometry(f"{dim}x{dim}+{x}+{y}")
        self.canvas.configure(width=dim, height=dim)
        self.win.attributes("-alpha", max(0.1, int(c["opacity"]) / 100))
        self.canvas.delete("all")
        self._color_items = []
        self._outline_items = []
        r = size + gap
        self._region = (sw // 2 + int(c["offset_x"]) - r, sh // 2 + int(c["offset_y"]) - r, 2 * r + 1, 2 * r + 1)
        bg = self._sample_bg() if c.get("color_mode") == "Moslashuvchan" else None
        color, edge = current_colors(c, bg=bg)
        self._last_colors = (color, edge)
        half = th / 2

        def bar(x0, y0, x1, y1):
            if outline:
                o = self.canvas.create_rectangle(x0 - 1, y0 - 1, x1 + 1, y1 + 1, fill=edge, outline="")
                self._outline_items.append((o, "fill"))
            item = self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            self._color_items.append((item, "fill"))

        def line(x0, y0, x1, y1):
            if outline:
                o = self.canvas.create_line(x0, y0, x1, y1, fill=edge, width=th + 2)
                self._outline_items.append((o, "fill"))
            item = self.canvas.create_line(x0, y0, x1, y1, fill=color, width=th)
            self._color_items.append((item, "fill"))

        def ring(r):
            if outline:
                o = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=edge, width=th + 2)
                self._outline_items.append((o, "outline"))
            item = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=th)
            self._color_items.append((item, "outline"))

        def dot():
            r = max(1.0, half)
            bar(cx - r, cy - r, cx + r, cy + r)

        if style in ("Plyus", "Plyus + nuqta", "T-shakl"):
            if style != "T-shakl":
                bar(cx - half, cy - gap - size, cx + half, cy - gap)
            bar(cx - half, cy + gap, cx + half, cy + gap + size)
            bar(cx - gap - size, cy - half, cx - gap, cy + half)
            bar(cx + gap, cy - half, cx + gap + size, cy + half)
            if style == "Plyus + nuqta":
                dot()
        elif style == "X-shakl":
            d0, d1 = gap * 0.7, (gap + size) * 0.7
            line(cx - d1, cy - d1, cx - d0, cy - d0)
            line(cx + d0, cy + d0, cx + d1, cy + d1)
            line(cx + d1, cy - d1, cx + d0, cy - d0)
            line(cx - d0, cy + d0, cx - d1, cy + d1)
        elif style in ("Doira", "Doira + nuqta"):
            ring(max(2, size))
            if style == "Doira + nuqta":
                dot()
        if style == "Nuqta" or (c["dot"] and style not in ("Nuqta", "Plyus + nuqta", "Doira + nuqta")):
            dot()
