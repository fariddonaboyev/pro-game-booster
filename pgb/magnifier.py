import tkinter as tk

from . import winapi

SHAPES = ["Doira", "Kvadrat"]
MODES = ["Yoqib-o'chirish", "Bosib turish"]


class Magnifier:
    """Lens at screen centre that shows the centre zoomed in; click-through and hidden from capture."""

    def __init__(self, root, cfg, on_shown=None):
        self.root = root
        self.cfg = cfg
        self.on_shown = on_shown
        self.win = None
        self.hwnd = None
        self.draw_hwnd = None
        self._job = None
        self._pen = None
        self._pen_key = None

    @property
    def visible(self):
        return self.win is not None

    def toggle(self):
        self.hide() if self.visible else self.show()

    def show(self):
        if self.win:
            self.apply()
            return
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#000000")
        self.apply()
        self.hwnd = winapi.make_overlay(self.win)
        self.draw_hwnd = self.win.winfo_id()
        if self.on_shown:
            self.on_shown()
        self._loop()

    def hide(self):
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        if self.win:
            self.win.destroy()
        self.win = self.hwnd = self.draw_hwnd = None
        self._free_pen()

    def _geometry(self):
        c = self.cfg
        size = int(c["size"])
        sw, sh = winapi.screen_size()
        cx, cy = sw // 2 + int(c["offset_x"]), sh // 2 + int(c["offset_y"])
        return size, cx, cy

    def apply(self):
        if not self.win:
            return
        size, cx, cy = self._geometry()
        self.win.geometry(f"{size}x{size}+{cx - size // 2}+{cy - size // 2}")
        if winapi.IS_WIN:
            self.win.update_idletasks()
            hwnd = winapi.toplevel_hwnd(self.win)
            rgn = winapi.gdi32.CreateEllipticRgn(0, 0, size + 1, size + 1) if self.cfg["shape"] == "Doira" else None
            winapi.user32.SetWindowRgn(hwnd, rgn, True)

    def _free_pen(self):
        if self._pen and winapi.IS_WIN:
            winapi.gdi32.DeleteObject(self._pen)
        self._pen = self._pen_key = None

    def _loop(self):
        if not self.win:
            return
        try:
            self._draw()
        except OSError:
            pass
        fps = max(10, min(144, int(self.cfg.get("fps", 60))))
        self._job = self.root.after(int(1000 / fps), self._loop)

    def _draw(self):
        if not winapi.IS_WIN:
            return
        c = self.cfg
        size, cx, cy = self._geometry()
        zoom = max(1.1, float(c["zoom"]))
        src = max(4, int(size / zoom))
        u, g = winapi.user32, winapi.gdi32
        screen = u.GetDC(None)
        dc = u.GetDC(self.draw_hwnd)
        try:
            g.SetStretchBltMode(dc, winapi.HALFTONE if c["smooth"] else winapi.COLORONCOLOR)
            g.SetBrushOrgEx(dc, 0, 0, None)
            g.StretchBlt(dc, 0, 0, size, size, screen, cx - src // 2, cy - src // 2, src, src, winapi.SRCCOPY)
            if c["border"]:
                key = (c["border_color"], max(2, size // 90))
                if key != self._pen_key:
                    self._free_pen()
                    self._pen = g.CreatePen(0, key[1], winapi.colorref(key[0]))
                    self._pen_key = key
                old_pen = g.SelectObject(dc, self._pen)
                old_brush = g.SelectObject(dc, g.GetStockObject(winapi.NULL_BRUSH))
                half = key[1] // 2
                shape = g.Ellipse if c["shape"] == "Doira" else g.Rectangle
                shape(dc, half, half, size - half + 1, size - half + 1)
                g.SelectObject(dc, old_pen)
                g.SelectObject(dc, old_brush)
        finally:
            u.ReleaseDC(self.draw_hwnd, dc)
            u.ReleaseDC(None, screen)
        winapi.keep_on_top(self.hwnd)
