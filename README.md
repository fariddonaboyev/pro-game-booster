# PRO Game Booster

Windows uchun o'yin yordamchisi (CS2 va boshqa o'yinlar):

- **Nishon (crosshair) overlay** — ekran o'rtasida, 7 shakl; rang rejimlari: *Moslashuvchan* (fonga qarab qora/oq/teskari rang), *Bitta rang*, *Kamalak*.
- **Lupa** — ekran markazini 1.0x–6x kattalashtiradi, o'lchami 50 px dan to'liq ekrangacha; o'lcham, shakl, ramka, FPS sozlanadi; yoqib-o'chirish yoki bosib turish rejimi.
- **Booster** — keraksiz dasturlarni yopish, RAMni bo'shatish, yuqori unumdorlik quvvat rejimi, TEMP/DNS tozalash, o'yinga yuqori prioritet.
- **CS2 / Ekran** — Keng (16:9), O'rtacha (16:10), Tor (4:3 cho'zilgan) rejimlari; Windows ruxsatini almashtirish va `autoexec.cfg` (HUD, radar, viewmodel) yozish.

Standart tugmalar: F6 nishon, F7 lupa, Num +/- lupa zoom, F8 boost, F9 asl ruxsat.

Overlay va lupa faqat **Fullscreen Windowed** rejimida ko'rinadi. Windows 10 2004+ / 11.

## Build

GitHub Actions (`build-windows.yml`) har `main` push'da faqat o'rnatuvchini (`PROGameBooster-Setup.exe`) artifact sifatida yuklaydi.

Qo'lda: `pip install -r requirements.txt pyinstaller` → `pyinstaller --onefile --windowed --uac-admin --name PROGameBooster main.py`.
