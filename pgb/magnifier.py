import ctypes
import tkinter as tk

from . import winapi

SHAPES = ["Doira", "Kvadrat"]
QUALITY = ["Maksimal silliq", "Silliq", "Tez (piksel)"]
MARGIN = 3  # extra source pixels so the bicubic kernel has real neighbours at the lens edge
MODES = ["Yoqib-o'chirish", "Bosib turish"]
RING_KEY = "#010101"


class Magnifier:
    """Click-through lens at screen centre. Smooth mode: double-buffered GDI StretchBlt with HALFTONE filtering;
    fast mode: Windows Magnification API (nearest-neighbour pixels)."""

    def __init__(self, root, cfg, on_shown=None, exclude=None):
        self.root = root
        self.cfg = cfg
        self.on_shown = on_shown
        self.exclude = exclude or list
        self.win = self.ring = None
        self.hwnd = self.ring_hwnd = self.mag_hwnd = None
        self._job = None
        self._filter = None
        self._zoom = None
        self._renderer = SmoothRenderer()

    @property
    def visible(self):
        return self.win is not None

    def toggle(self):
        self.hide() if self.visible else self.show()

    def restart(self):
        if self.visible:
            self.hide()
            self.show()

    def show(self):
        if self.win:
            self.apply()
            return
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        use_mag = winapi.mag is not None and self.cfg.get("quality") == QUALITY[2]
        self.win.configure(bg="#000000" if use_mag else "")
        self._place(self.win)
        self.hwnd = winapi.make_overlay(self.win, exclude_from_capture=not use_mag)
        if winapi.IS_WIN:
            winapi.user32.SetLayeredWindowAttributes(self.hwnd, 0, 255, winapi.LWA_ALPHA)
            if use_mag:
                size = int(self.cfg["size"])
                self.mag_hwnd = winapi.user32.CreateWindowExW(
                    0, "Magnifier", "PROLupa", winapi.WS_CHILD | winapi.WS_VISIBLE, 0, 0, size, size,
                    self.hwnd, None, winapi.kernel32.GetModuleHandleW(None), None)
        self._make_ring()
        self.apply()
        if self.on_shown:
            self.on_shown()
        self._loop()

    def hide(self):
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        if self.mag_hwnd:
            winapi.user32.DestroyWindow(self.mag_hwnd)
        for w in (self.ring, self.win):
            if w:
                w.destroy()
        self.win = self.ring = self.hwnd = self.ring_hwnd = self.mag_hwnd = None
        self._filter = self._zoom = None
        self._renderer.free()

    def _geometry(self):
        c = self.cfg
        size = int(c["size"])
        sw, sh = winapi.screen_size()
        return size, sw // 2 + int(c["offset_x"]), sh // 2 + int(c["offset_y"])

    def _place(self, w):
        size, cx, cy = self._geometry()
        w.geometry(f"{size}x{size}+{cx - size // 2}+{cy - size // 2}")

    def _make_ring(self):
        self.ring = tk.Toplevel(self.root)
        self.ring.overrideredirect(True)
        self.ring.attributes("-topmost", True)
        self.ring.configure(bg=RING_KEY)
        if winapi.IS_WIN:
            self.ring.attributes("-transparentcolor", RING_KEY)
        self.ring_canvas = tk.Canvas(self.ring, bg=RING_KEY, highlightthickness=0, bd=0)
        self.ring_canvas.pack(fill="both", expand=True)
        self.ring_hwnd = winapi.make_overlay(self.ring)

    def apply(self):
        if not self.win:
            return
        c = self.cfg
        size, _, _ = self._geometry()
        self._place(self.win)
        self._place(self.ring)
        self._zoom = None
        if winapi.IS_WIN:
            self.win.update_idletasks()
            for hwnd in (self.hwnd, self.ring_hwnd):
                rgn = winapi.gdi32.CreateEllipticRgn(0, 0, size + 1, size + 1) if c["shape"] == "Doira" else None
                winapi.user32.SetWindowRgn(hwnd, rgn, True)
            if self.mag_hwnd:
                winapi.user32.MoveWindow(self.mag_hwnd, 0, 0, size, size, True)
        rc = self.ring_canvas
        rc.delete("all")
        rc.configure(width=size, height=size)
        if c["border"]:
            w = max(2, size // 90)
            color = "#020202" if c["border_color"].lower() == RING_KEY else c["border_color"]
            box = (w / 2 + 1, w / 2 + 1, size - w / 2 - 1, size - w / 2 - 1)
            (rc.create_oval if c["shape"] == "Doira" else rc.create_rectangle)(*box, outline=color, width=w)
        winapi.keep_on_top(self.hwnd)
        winapi.keep_on_top(self.ring_hwnd)

    def _loop(self):
        if not self.win:
            return
        try:
            self._draw_mag() if self.mag_hwnd else self._draw_gdi()
        except OSError:
            pass
        winapi.keep_on_top(self.hwnd)
        winapi.keep_on_top(self.ring_hwnd)
        fps = max(10, min(240, int(self.cfg.get("fps", 120))))
        self._job = self.root.after(max(1, int(1000 / fps)), self._loop)

    def _source(self):
        size, cx, cy = self._geometry()
        zoom = max(1.0, float(self.cfg["zoom"]))
        src = size / zoom
        left, top = round(cx - src / 2), round(cy - src / 2)
        return size, zoom, left, top, max(4, round(src))

    def _draw_mag(self):
        _, zoom, left, top, src = self._source()
        m = winapi.mag
        if zoom != self._zoom:
            t = winapi.MAGTRANSFORM()
            t.v[0], t.v[4], t.v[8] = zoom, zoom, 1.0
            m.MagSetWindowTransform(self.mag_hwnd, ctypes.byref(t))
            self._zoom = zoom
        hwnds = tuple(h for h in (self.hwnd, self.ring_hwnd, *self.exclude()) if h)
        if hwnds != self._filter:
            arr = (winapi.wintypes.HWND * len(hwnds))(*hwnds)
            m.MagSetWindowFilterList(self.mag_hwnd, winapi.MW_FILTERMODE_EXCLUDE, len(hwnds), arr)
            self._filter = hwnds
        m.MagSetWindowSource(self.mag_hwnd, winapi.RECT(left, top, left + src, top + src))
        winapi.user32.InvalidateRect(self.mag_hwnd, None, True)

    def _draw_gdi(self):
        if not winapi.IS_WIN:
            return
        size, _, left, top, src = self._source()
        bicubic = self.cfg.get("quality") == QUALITY[0] and winapi.gdiplus is not None
        self._renderer.draw(self.win.winfo_id(), size, left, top, src, bicubic)


class SmoothRenderer:
    """Screen region -> scaled lens image, double-buffered. Bicubic via GDI+, otherwise GDI HALFTONE.
    Buffers are kept between frames and rebuilt only when the size changes."""

    def __init__(self):
        self.key = None
        self.src_dc = self.src_bmp = self.src_old = self.bitmap = None
        self.dst_dc = self.dst_bmp = self.dst_old = self.graphics = None

    def free(self):
        if not winapi.IS_WIN or self.key is None:
            self.key = None
            return
        g, gp = winapi.gdi32, winapi.gdiplus
        if self.graphics:
            gp.GdipDeleteGraphics(self.graphics)
        if self.bitmap:
            gp.GdipDisposeImage(self.bitmap)
        for dc, bmp, old in ((self.src_dc, self.src_bmp, self.src_old), (self.dst_dc, self.dst_bmp, self.dst_old)):
            if dc:
                g.SelectObject(dc, old)
                g.DeleteObject(bmp)
                g.DeleteDC(dc)
        self.__init__()

    def _ensure(self, ref_dc, size, cap, bicubic):
        key = (size, cap, bicubic)
        if key == self.key:
            return
        self.free()
        g, gp = winapi.gdi32, winapi.gdiplus
        self.src_dc = g.CreateCompatibleDC(ref_dc)
        bits = ctypes.c_void_p()
        bih = winapi.BITMAPINFOHEADER(ctypes.sizeof(winapi.BITMAPINFOHEADER), cap, -cap, 1, 32, 0, 0, 0, 0, 0, 0)
        self.src_bmp = g.CreateDIBSection(ref_dc, ctypes.byref(bih), 0, ctypes.byref(bits), None, 0)
        self.src_old = g.SelectObject(self.src_dc, self.src_bmp)
        self.dst_dc = g.CreateCompatibleDC(ref_dc)
        self.dst_bmp = g.CreateCompatibleBitmap(ref_dc, size, size)
        self.dst_old = g.SelectObject(self.dst_dc, self.dst_bmp)
        if bicubic:
            self.bitmap, self.graphics = ctypes.c_void_p(), ctypes.c_void_p()
            gp.GdipCreateBitmapFromScan0(cap, cap, cap * 4, 0x00022009, bits, ctypes.byref(self.bitmap))
            gp.GdipCreateFromHDC(self.dst_dc, ctypes.byref(self.graphics))
            gp.GdipSetCompositingMode(self.graphics, 1)  # SourceCopy
            gp.GdipSetInterpolationMode(self.graphics, 7)  # HighQualityBicubic
            gp.GdipSetPixelOffsetMode(self.graphics, 2)  # HighQuality
        else:
            g.SetStretchBltMode(self.dst_dc, winapi.HALFTONE)
            g.SetBrushOrgEx(self.dst_dc, 0, 0, None)
        self.key = key

    def draw(self, hwnd, size, left, top, src, bicubic):
        u, g = winapi.user32, winapi.gdi32
        cap = src + 2 * MARGIN
        screen = u.GetDC(None)
        dc = u.GetDC(hwnd)
        try:
            self._ensure(dc, size, cap, bicubic)
            g.BitBlt(self.src_dc, 0, 0, cap, cap, screen, left - MARGIN, top - MARGIN, winapi.SRCCOPY)
            if bicubic:
                g.GdiFlush()
                winapi.gdiplus.GdipDrawImageRectRectI(self.graphics, self.bitmap, 0, 0, size, size,
                                                      MARGIN, MARGIN, src, src, 2, None, None, None)
            else:
                g.StretchBlt(self.dst_dc, 0, 0, size, size, self.src_dc, MARGIN, MARGIN, src, src, winapi.SRCCOPY)
            g.BitBlt(dc, 0, 0, size, size, self.dst_dc, 0, 0, winapi.SRCCOPY)
        finally:
            u.ReleaseDC(hwnd, dc)
            u.ReleaseDC(None, screen)
