import queue
import threading
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from . import __version__, booster, cs2, display, settings, winapi
from .crosshair import COLOR_MODES, PRESET_COLORS, STYLES, CrosshairOverlay
from .magnifier import MODES, SHAPES, Magnifier

HOTKEYS = list(winapi.KEYS)


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = settings.load()
        self.crosshair = CrosshairOverlay(root, self.cfg["crosshair"])
        self.lupa = Magnifier(root, self.cfg["lupa"], on_shown=self.crosshair.lift,
                              exclude=lambda: [self.crosshair.hwnd])
        self.events = queue.Queue()
        self._pressed = {}
        self._save_job = None
        self.res_changed = False
        self.native = display.native_mode()

        root.title(f"PRO Game Booster {__version__}")
        root.geometry("560x680")
        root.minsize(520, 600)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_crosshair(self._tab(nb, "Nishon"))
        self.tab_lupa(self._tab(nb, "Lupa"))
        self.tab_booster(self._tab(nb, "Booster"))
        self.tab_cs2(self._tab(nb, "CS2 / Ekran"))

        self.status = tk.StringVar()
        ttk.Label(root, textvariable=self.status, anchor="w").pack(fill="x", padx=10, pady=(0, 8))
        self.update_status()
        self.root.after(15, self.poll_keys)
        self.root.after(100, self.poll_events)

    # ---------- helpers ----------
    def _tab(self, nb, title):
        frame = ttk.Frame(nb, padding=10)
        nb.add(frame, text=title)
        frame.columnconfigure(1, weight=1)
        return frame

    def _row(self, parent):
        return parent.grid_size()[1]

    def save_later(self):
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(400, lambda: settings.save(self.cfg))

    def _changed(self, callback):
        def run():
            self.save_later()
            self.update_status()
            if callback:
                callback()
        return run

    def scale(self, parent, label, section, key, lo, hi, step=1, cb=None):
        r = self._row(parent)
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=2)
        is_float = isinstance(step, float)
        var = tk.DoubleVar(value=self.cfg[section][key])
        done = self._changed(cb)

        def on_move(_=None):
            value = round(var.get() / step) * step
            self.cfg[section][key] = round(value, 2) if is_float else int(value)
            done()
        tk.Scale(parent, from_=lo, to=hi, resolution=step, orient="horizontal", variable=var,
                 command=on_move, showvalue=True, length=260).grid(row=r, column=1, sticky="we")
        return var

    def combo(self, parent, label, section, key, values, cb=None):
        r = self._row(parent)
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=self.cfg[section][key])
        box = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        box.grid(row=r, column=1, sticky="we", pady=2)
        done = self._changed(cb)

        def on_pick(_=None):
            self.cfg[section][key] = var.get()
            done()
        box.bind("<<ComboboxSelected>>", on_pick)
        return var

    def check(self, parent, label, section, key, cb=None):
        var = tk.BooleanVar(value=self.cfg[section][key])
        done = self._changed(cb)

        def on_click():
            self.cfg[section][key] = var.get()
            done()
        ttk.Checkbutton(parent, text=label, variable=var, command=on_click).grid(
            row=self._row(parent), column=0, columnspan=2, sticky="w", pady=2)
        return var

    def note(self, parent, text):
        ttk.Label(parent, text=text, foreground="#555", wraplength=500, justify="left").grid(
            row=self._row(parent), column=0, columnspan=2, sticky="w", pady=(6, 2))

    # ---------- Nishon ----------
    def tab_crosshair(self, f):
        c = "crosshair"
        redraw = self.crosshair.redraw
        self.btn_cross = ttk.Button(f, command=self.toggle_crosshair)
        self.btn_cross.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 8))
        self.combo(f, "Shakl", c, "style", STYLES, redraw)
        self.color_mode_var = self.combo(f, "Rang rejimi", c, "color_mode", COLOR_MODES, redraw)
        r = self._row(f)
        ttk.Label(f, text="Rang").grid(row=r, column=0, sticky="w")
        colors = ttk.Frame(f)
        colors.grid(row=r, column=1, sticky="w", pady=2)
        self.color_preview = tk.Label(colors, width=3, bg=self.cfg[c]["color"], relief="solid", bd=1)
        self.color_preview.pack(side="left", padx=(0, 6))
        for col in PRESET_COLORS:
            tk.Button(colors, bg=col, activebackground=col, width=2, relief="flat",
                      command=lambda v=col: self.set_color(v)).pack(side="left", padx=1)
        ttk.Button(colors, text="Boshqa...", command=self.pick_color).pack(side="left", padx=(6, 0))
        self.scale(f, "Kamalak tezligi", c, "rainbow_speed", 1, 20)
        self.scale(f, "Uzunlik", c, "size", 0, 40, cb=redraw)
        self.scale(f, "Qalinlik", c, "thickness", 1, 10, cb=redraw)
        self.scale(f, "Oraliq (gap)", c, "gap", 0, 30, cb=redraw)
        self.scale(f, "Shaffoflik %", c, "opacity", 10, 100, cb=redraw)
        self.scale(f, "Siljitish X", c, "offset_x", -100, 100, cb=redraw)
        self.scale(f, "Siljitish Y", c, "offset_y", -100, 100, cb=redraw)
        self.check(f, "Kontur (qora/oq chegara)", c, "outline", redraw)
        self.check(f, "Markazda nuqta", c, "dot", redraw)
        self.combo(f, "Yoqish tugmasi", c, "hotkey", HOTKEYS)
        self.note(f, "Moslashuvchan: nishon orqasidagi fonga qarab rang avtomatik almashadi "
                     "(qorong'ida oq, yorug'da qora, rangli fonda teskari rang). "
                     "O'yinni 'Fullscreen Windowed' (oynali to'liq ekran) rejimida o'ynang.")
        self._refresh_buttons()

    def set_color(self, color):
        self.cfg["crosshair"]["color"] = color
        self.cfg["crosshair"]["color_mode"] = "Bitta rang"
        self.color_mode_var.set("Bitta rang")
        self.color_preview.configure(bg=color)
        self.crosshair.redraw()
        self.save_later()

    def pick_color(self):
        color = colorchooser.askcolor(self.cfg["crosshair"]["color"], title="Nishon rangi")[1]
        if color:
            self.set_color(color)

    def toggle_crosshair(self):
        self.crosshair.toggle()
        self._refresh_buttons()

    # ---------- Lupa ----------
    def tab_lupa(self, f):
        c = "lupa"
        apply = self.lupa.apply
        self.btn_lupa = ttk.Button(f, command=self.toggle_lupa)
        self.btn_lupa.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 8))
        self.zoom_var = self.scale(f, "Kattalashtirish (x)", c, "zoom", 1.5, 6.0, 0.5)
        self.scale(f, "O'lcham (px)", c, "size", 120, 700, 10, apply)
        self.combo(f, "Shakl", c, "shape", SHAPES, apply)
        self.check(f, "Ramka", c, "border", apply)
        r = self._row(f)
        ttk.Label(f, text="Ramka rangi").grid(row=r, column=0, sticky="w")
        self.border_preview = tk.Button(f, width=3, bg=self.cfg[c]["border_color"], command=self.pick_border)
        self.border_preview.grid(row=r, column=1, sticky="w", pady=2)
        self.check(f, "Silliq tasvir (faqat zaxira GDI rejimida)", c, "smooth")
        self.scale(f, "Yangilanish (FPS)", c, "fps", 20, 144, 2)
        self.scale(f, "Siljitish X", c, "offset_x", -400, 400, 5, apply)
        self.scale(f, "Siljitish Y", c, "offset_y", -400, 400, 5, apply)
        self.combo(f, "Rejim", c, "mode", MODES)
        self.combo(f, "Lupa tugmasi", c, "hotkey", HOTKEYS)
        self.combo(f, "Kattalashtirish +", c, "zoom_in", HOTKEYS)
        self.combo(f, "Kattalashtirish -", c, "zoom_out", HOTKEYS)
        self.note(f, "Lupa ekran markazini kattalashtirib ko'rsatadi, sichqoncha bosishlari undan o'tib ketadi. "
                     "'Bosib turish' rejimida tugmani bosib turganingizda chiqadi. Windows 10 (2004+) yoki 11 kerak.")
        self._refresh_buttons()

    def pick_border(self):
        color = colorchooser.askcolor(self.cfg["lupa"]["border_color"], title="Ramka rangi")[1]
        if color:
            self.cfg["lupa"]["border_color"] = color
            self.border_preview.configure(bg=color)
            self.lupa.apply()
            self.save_later()

    def toggle_lupa(self):
        self.lupa.toggle()
        self.crosshair.lift()
        self._refresh_buttons()

    def change_zoom(self, delta):
        z = min(6.0, max(1.5, float(self.cfg["lupa"]["zoom"]) + delta))
        self.cfg["lupa"]["zoom"] = z
        self.zoom_var.set(z)
        self.save_later()

    # ---------- Booster ----------
    def tab_booster(self, f):
        c = "booster"
        f.rowconfigure(1, weight=1)
        ttk.Label(f, text="Yopiladigan dasturlar (belgilang):").grid(row=0, column=0, columnspan=2, sticky="w")
        box = ttk.Frame(f)
        box.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=4)
        self.proc_list = tk.Listbox(box, selectmode="multiple", height=12, activestyle="none")
        sb = ttk.Scrollbar(box, command=self.proc_list.yview)
        self.proc_list.configure(yscrollcommand=sb.set)
        self.proc_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        ttk.Button(f, text="Ro'yxatni yangilash", command=self.refresh_procs).grid(
            row=2, column=0, columnspan=2, sticky="we")
        r = self._row(f)
        ttk.Label(f, text="O'yin (exe)").grid(row=r, column=0, sticky="w", pady=4)
        self.game_var = tk.StringVar(value=self.cfg[c]["game"])
        ttk.Entry(f, textvariable=self.game_var).grid(row=r, column=1, sticky="we")
        self.check(f, "Yuqori unumdorlik quvvat rejimi", c, "power_plan")
        self.check(f, "RAMni tozalash (fon dasturlar xotirasini bo'shatish)", c, "trim_ram")
        self.check(f, "Vaqtinchalik fayllarni o'chirish (%TEMP%)", c, "clean_temp")
        self.check(f, "DNS keshini tozalash (ping uchun)", c, "flush_dns")
        self.combo(f, "Boost tugmasi", c, "hotkey", HOTKEYS)
        btns = ttk.Frame(f)
        btns.grid(row=self._row(f), column=0, columnspan=2, sticky="we", pady=6)
        ttk.Button(btns, text="BOOST", command=self.run_boost).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="Quvvat rejimini qaytarish", command=self.restore_power).pack(
            side="left", expand=True, fill="x", padx=(6, 0))
        self.log = tk.Text(f, height=6, state="disabled", wrap="word")
        self.log.grid(row=self._row(f), column=0, columnspan=2, sticky="we")
        self.refresh_procs()

    def refresh_procs(self):
        chosen = set(self.cfg["booster"]["kill"]) or booster.SUGGESTED
        self.procs = booster.list_processes()
        self.proc_list.delete(0, "end")
        for i, (name, mb, pids) in enumerate(self.procs):
            self.proc_list.insert("end", f"{name}  —  {mb:.0f} MB  ({len(pids)})")
            if name in chosen:
                self.proc_list.selection_set(i)

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def run_boost(self):
        b = self.cfg["booster"]
        b["game"] = self.game_var.get().strip()
        b["kill"] = [self.procs[i][0] for i in self.proc_list.curselection()]
        self.save_later()
        opts = dict(b)
        self.write_log("Boost boshlandi...")
        threading.Thread(target=self._boost_worker, args=(opts,), daemon=True).start()

    def _boost_worker(self, b):
        def say(text):
            self.events.put(("log", text))

        before = booster.ram_used_mb()
        if b["kill"]:
            say(f"Yopildi: {booster.kill_names(b['kill'])} ta jarayon")
        if b["trim_ram"]:
            say(f"RAM tozalandi: {booster.trim_ram()} ta jarayon")
        if b["power_plan"]:
            prev = booster.set_max_performance()
            if prev and prev != booster.HIGH_PERF:
                self.events.put(("prev_plan", prev))
            say("Quvvat rejimi: Yuqori unumdorlik")
        if b["clean_temp"]:
            say(f"TEMP tozalandi: {booster.clean_temp():.0f} MB")
        if b["flush_dns"]:
            booster.flush_dns()
            say("DNS keshi tozalandi")
        if b["game"]:
            n = booster.boost_game(b["game"])
            say(f"{b['game']}: yuqori prioritet" if n else f"{b['game']} ishlamayapti (o'yinni ochib, qayta bosing)")
        say(f"Bo'shagan RAM: {max(0.0, before - booster.ram_used_mb()):.0f} MB. Tayyor!")
        self.events.put(("refresh", None))

    def restore_power(self):
        booster.restore_power_plan(self.cfg["booster"]["prev_power_plan"])
        self.write_log("Quvvat rejimi asliga qaytarildi")

    # ---------- CS2 / Ekran ----------
    def tab_cs2(self, f):
        c = "cs2"
        self.res_label = tk.StringVar()
        ttk.Label(f, textvariable=self.res_label, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        presets = ttk.Frame(f)
        presets.grid(row=1, column=0, columnspan=2, sticky="we", pady=6)
        for name in cs2.PRESETS:
            ttk.Button(presets, text=name, command=lambda n=name: self.apply_preset(n)).pack(fill="x", pady=1)
        ttk.Button(presets, text="Asl ruxsatga qaytarish", command=self.restore_resolution).pack(fill="x", pady=1)
        r = self._row(f)
        ttk.Label(f, text="Boshqa ruxsat").grid(row=r, column=0, sticky="w")
        row = ttk.Frame(f)
        row.grid(row=r, column=1, sticky="we")
        self.modes = display.list_modes()
        self.mode_var = tk.StringVar()
        ttk.Combobox(row, textvariable=self.mode_var, state="readonly", width=18,
                     values=[f"{w}x{h} @{hz}Hz" for w, h, hz in self.modes]).pack(side="left")
        ttk.Button(row, text="Qo'llash", command=self.apply_custom_mode).pack(side="left", padx=4)
        self.check(f, "Cho'zish (qora chiziqsiz, stretched)", c, "stretch")
        self.combo(f, "Asl ruxsat tugmasi", c, "restore_hotkey", HOTKEYS)
        ttk.Separator(f).grid(row=self._row(f), column=0, columnspan=2, sticky="we", pady=6)
        self.scale(f, "HUD o'lchami", c, "hud_scaling", 0.5, 0.95, 0.05)
        self.scale(f, "Radar o'lchami", c, "radar_hud_scale", 0.8, 1.3, 0.05)
        self.scale(f, "Radar masshtabi", c, "radar_scale", 0.25, 1.0, 0.05)
        self.check(f, "Radar doim markazda", c, "radar_centered")
        self.scale(f, "Qurol FOV (viewmodel)", c, "viewmodel_fov", 54, 68)
        self.scale(f, "fps_max (0 = cheksiz)", c, "fps_max", 0, 500, 10)
        self.combo(f, "O'yin crosshairi", c, "game_crosshair", cs2.GAME_CROSSHAIR)
        ttk.Button(f, text="autoexec.cfg ga yozish", command=lambda: self.write_cfg(None)).grid(
            row=self._row(f), column=0, columnspan=2, sticky="we", pady=4)
        r = self._row(f)
        ttk.Label(f, text=f"Steam launch options: {cs2.LAUNCH_OPTIONS}").grid(row=r, column=0, sticky="w")
        ttk.Button(f, text="Nusxalash", command=self.copy_launch).grid(row=r, column=1, sticky="e")
        self.note(f, "Asosiy FOV CS2'da 90° ga qulflangan (o'zgartirish = VAC ban), shuning uchun ko'rinish "
                     "ekran nisbati orqali o'zgaradi. 4:3 cho'zilgan uchun CS2'da Display Mode = "
                     "'Fullscreen Windowed' qiling; qora chiziq chiqsa NVIDIA/AMD panelida Scaling = "
                     "'Full-screen' ni yoqing. Dasturni yopganda ruxsat avtomatik qaytadi.")
        self.update_res_label()

    def update_res_label(self):
        w, h, hz = display.current_mode()
        self.res_label.set(f"Hozirgi ruxsat: {w}x{h} @{hz}Hz   (asl: {self.native[0]}x{self.native[1]})")
        self.crosshair.redraw()
        self.lupa.apply()

    def _set_mode(self, mode, stretch):
        if mode is None:
            messagebox.showwarning("Ruxsat", "Monitoringiz bu nisbatni qo'llab-quvvatlamaydi.")
            return False
        ok = display.set_mode(mode[0], mode[1], mode[2], stretch)
        if ok:
            self.res_changed = (mode[0], mode[1]) != self.native[:2]
        else:
            messagebox.showerror("Ruxsat", f"{mode[0]}x{mode[1]} o'rnatilmadi.")
        self.root.after(800, self.update_res_label)
        return ok

    def apply_preset(self, name):
        p = cs2.PRESETS[name]
        if not p["heights"] and abs(self.native[0] / self.native[1] - p["aspect"]) < 0.02:
            mode = self.native
        else:
            mode = display.pick_mode(p["aspect"], p["heights"]) or (self.native if not p["heights"] else None)
        if self._set_mode(mode, p["stretch"] and self.cfg["cs2"]["stretch"]):
            self.write_cfg(p["cfg"], quiet=True)

    def apply_custom_mode(self):
        i = [f"{w}x{h} @{hz}Hz" for w, h, hz in self.modes].index(self.mode_var.get()) \
            if self.mode_var.get() else -1
        if i >= 0:
            self._set_mode(self.modes[i], self.cfg["cs2"]["stretch"])

    def restore_resolution(self):
        display.restore()
        self.res_changed = False
        self.root.after(800, self.update_res_label)

    def write_cfg(self, preset_cfg, quiet=False):
        folder = cs2.find_cfg_dir()
        if not folder:
            if not quiet:
                messagebox.showwarning("CS2", "CS2 cfg papkasi topilmadi (Steam o'rnatilganmi?).")
            return
        try:
            path = cs2.write_autoexec(folder, cs2.build_cfg(self.cfg["cs2"], preset_cfg))
        except OSError as e:
            messagebox.showerror("CS2", f"Yozib bo'lmadi: {e}")
            return
        if not quiet:
            messagebox.showinfo("CS2", f"Yozildi:\n{path}\n\nSteam launch options ga '{cs2.LAUNCH_OPTIONS}' "
                                       "qo'shing yoki konsolda 'exec autoexec' yozing.")

    def copy_launch(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(cs2.LAUNCH_OPTIONS)

    # ---------- loop ----------
    def _edge(self, name):
        down = winapi.key_down(name)
        was = self._pressed.get(name, False)
        self._pressed[name] = down
        return down and not was

    def poll_keys(self):
        cc, lc, bc, sc = self.cfg["crosshair"], self.cfg["lupa"], self.cfg["booster"], self.cfg["cs2"]
        if self._edge(cc["hotkey"]):
            self.toggle_crosshair()
        if lc["mode"] == "Bosib turish":
            held = winapi.key_down(lc["hotkey"])
            if held != self.lupa.visible:
                self.toggle_lupa()
        elif self._edge(lc["hotkey"]):
            self.toggle_lupa()
        if self._edge(lc["zoom_in"]):
            self.change_zoom(0.5)
        if self._edge(lc["zoom_out"]):
            self.change_zoom(-0.5)
        if self._edge(bc["hotkey"]):
            self.run_boost()
        if self._edge(sc["restore_hotkey"]):
            self.restore_resolution()
        self.root.after(15, self.poll_keys)

    def poll_events(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.write_log(value)
            elif kind == "prev_plan":
                self.cfg["booster"]["prev_power_plan"] = value
                self.save_later()
            elif kind == "refresh":
                self.refresh_procs()
        self.root.after(100, self.poll_events)

    def _refresh_buttons(self):
        if hasattr(self, "btn_cross"):
            on = self.crosshair.visible
            self.btn_cross.configure(text=("Nishonni o'chirish" if on else "Nishonni yoqish")
                                     + f"  [{self.cfg['crosshair']['hotkey']}]")
        if hasattr(self, "btn_lupa"):
            on = self.lupa.visible
            self.btn_lupa.configure(text=("Lupani o'chirish" if on else "Lupani yoqish")
                                    + f"  [{self.cfg['lupa']['hotkey']}]")

    def update_status(self):
        c = self.cfg
        self.status.set(f"Nishon: {c['crosshair']['hotkey']}  |  Lupa: {c['lupa']['hotkey']} "
                        f"({c['lupa']['zoom_in']}/{c['lupa']['zoom_out']})  |  Boost: {c['booster']['hotkey']}"
                        f"  |  Asl ruxsat: {c['cs2']['restore_hotkey']}")
        self._refresh_buttons()

    def on_close(self):
        if self.res_changed:
            display.restore()
        self.crosshair.hide()
        self.lupa.hide()
        settings.save(self.cfg)
        self.root.destroy()


def main():
    winapi.set_dpi_aware()
    root = tk.Tk()
    App(root)
    root.mainloop()
