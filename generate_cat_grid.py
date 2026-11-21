#!/usr/bin/env python3
"""GitHub etkinlik ızgarası: fareler yeşil karelerden çıkar, kedi zıplayıp patisiyle basar.

Kullanım:  python generate_cat_grid.py surmeliugur dist/cat-grid.svg
Bağımlılık yok (sadece standart kütüphane).
"""
import re
import sys
import urllib.request
from datetime import date, timedelta

CELL, GAP = 10, 3
PITCH = CELL + GAP
PAD_L, PAD_T, PAD_R, PAD_B = 70, 30, 12, 20
SLOT = 0.9          # her fare için saniye
LEAD = 1.0          # başlangıçta boş ızgarayla bekleme
RETURN = 1.0        # kedinin eve dönüşü
HOLD = 3.5          # dolu ızgara ekranda kalma süresi
FADE = 1.0          # karelerin sönmesi

LEVEL_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
LEVEL_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def fetch_cells(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "cat-grid-generator"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    cells = {}
    for tag in re.findall(r"<(?:td|rect)[^>]*data-date=\"[^\"]+\"[^>]*>", html):
        d = re.search(r'data-date="([^"]+)"', tag).group(1)
        lv = re.search(r'data-level="(\d)"', tag)
        cells[date.fromisoformat(d)] = int(lv.group(1)) if lv else 0
    if not cells:
        raise RuntimeError("Katkı verisi okunamadı")
    return cells


def layout(cells):
    first = min(cells)
    start = first - timedelta(days=(first.weekday() + 1) % 7)  # pazar
    out = []
    for d, lv in sorted(cells.items()):
        w = (d - start).days // 7
        r = (d.weekday() + 1) % 7
        out.append((d, w, r, lv))
    return out


def pct(t, total):
    return f"{t / total * 100:.3f}%"


def build_svg(cells):
    items = layout(cells)
    weeks = max(w for _, w, _, _ in items) + 1
    W = PAD_L + weeks * PITCH + PAD_R
    H = PAD_T + 7 * PITCH + PAD_B

    def center(w, r):
        return PAD_L + w * PITCH + CELL / 2, PAD_T + r * PITCH + CELL / 2

    events = [(w, r, lv) for _, w, r, lv in items if lv > 0]
    n = len(events)
    end = LEAD + n * SLOT                  # son fare ezildi
    D = end + RETURN + HOLD + FADE
    home = (PAD_L / 2, PAD_T + 3.5 * PITCH + 14)

    css = [
        ":root{--c0:%s;--c1:%s;--c2:%s;--c3:%s;--c4:%s;--cat:#1f2328}" % tuple(LEVEL_LIGHT),
        "@media(prefers-color-scheme:dark){:root{--c0:%s;--c1:%s;--c2:%s;--c3:%s;--c4:%s;"
        "--cat:#f0f6fc}}" % tuple(LEVEL_DARK),
        ".cat,.m{transform-origin:0 0}",
    ]

    # --- kedi ---
    kf = [(0.0, home[0], home[1], 1.0)]
    prev = home
    for i, (w, r, _) in enumerate(events):
        cx, cy = center(w, r)
        cy += 6
        s = LEAD + i * SLOT
        kf.append((s, prev[0], prev[1], 1.0))
        kf.append((s + 0.4 * SLOT, (prev[0] + cx) / 2, min(prev[1], cy) - 24, 1.0))
        kf.append((s + 0.62 * SLOT, cx, cy, 0.82))   # patiyle bas
        kf.append((s + 0.78 * SLOT, cx, cy, 1.0))
        prev = (cx, cy)
    kf.append((end, prev[0], prev[1], 1.0))
    kf.append((end + RETURN, home[0], home[1], 1.0))
    kf.append((D, home[0], home[1], 1.0))
    css.append("@keyframes cat{")
    for t, x, y, sy in kf:
        css.append(f"{pct(t, D)}{{transform:translate({x:.1f}px,{y:.1f}px) scale(1,{sy})}}")
    css.append("}")
    css.append(f".cat{{animation:cat {D:.2f}s ease-in-out infinite}}")

    # --- boş ızgara (tüm kareler başta boş) ---
    grid = []
    for _, w, r, lv in items:
        x, y = PAD_L + w * PITCH, PAD_T + r * PITCH
        grid.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="var(--c0)"/>'
        )

    # --- ezilince yeşile dönen katman + fare (aynı renk) ---
    overlays, mice = [], []
    for i, (w, r, lv) in enumerate(events):
        s = LEAD + i * SLOT
        hit = s + 0.62 * SLOT
        x, y = PAD_L + w * PITCH, PAD_T + r * PITCH
        css.append(
            f"@keyframes g{i}{{0%,{pct(hit, D)}{{opacity:0}}"
            f"{pct(hit + 0.08 * SLOT, D)},{pct(D - FADE, D)}{{opacity:1}}100%{{opacity:0}}}}"
            f".g{i}{{animation:g{i} {D:.2f}s linear infinite}}"
        )
        overlays.append(
            f'<rect class="g{i}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="var(--c{lv})" opacity="0"/>'
        )
        css.append(
            f"@keyframes m{i}{{0%,{pct(s, D)}{{transform:scale(0)}}"
            f"{pct(s + 0.2 * SLOT, D)},{pct(s + 0.6 * SLOT, D)}{{transform:scale(1)}}"
            f"{pct(s + 0.66 * SLOT, D)}{{transform:scale(1.4,.2)}}"
            f"{pct(s + 0.8 * SLOT, D)},100%{{transform:scale(0)}}}}"
            f".m{i}{{animation:m{i} {D:.2f}s linear infinite}}"
        )
        cx, cy = center(w, r)
        c = f"var(--c{lv})"
        mice.append(
            f'<g transform="translate({cx:.1f},{cy + 3:.1f})"><g class="m m{i}" fill="{c}">'
            f'<ellipse cx="0" cy="-3" rx="4.2" ry="3"/>'
            f'<circle cx="-3" cy="-6" r="1.8"/><circle cx="3" cy="-6" r="1.8"/>'
            f'<path d="M4 -2 q4 0 4 -4" stroke="{c}" stroke-width="1" fill="none"/>'
            f"</g></g>"
        )

    # --- GitHub logosundaki kedi siluetinden izlenmiş yol: ayak tabanı orijinde, 36px ---
    cat = (
        '<g class="cat" fill="var(--cat)">'
        '<path d="M-12.1 -35.9 L-12.5 -35.1 L-12.5 -34.8 L-12.6 -34.8 L-12.6 -34.5 L-12.7 -34.2 L-12.7 -33.8 L-12.8 -33.7 L-12.8 -33.2 L-12.9 -33.2 L-12.9 -31.9 L-12.8 -31.9 L-12.8 -31.3 L-12.7 -31.2 L-12.7 -30.6 L-12.4 -30.1 L-12.4 -29.8 L-13.1 -29.1 L-13.5 -28.4 L-13.6 -28.2 L-13.7 -28.1 L-14.0 -27.5 L-14.0 -27.3 L-14.2 -27.1 L-14.2 -27.0 L-14.5 -26.3 L-14.5 -26.0 L-14.6 -25.7 L-14.6 -25.3 L-14.7 -25.2 L-14.7 -24.8 L-14.8 -24.7 L-14.8 -22.4 L-14.7 -22.3 L-14.7 -21.6 L-14.6 -21.5 L-14.6 -21.1 L-14.5 -21.0 L-14.5 -20.3 L-14.4 -20.2 L-14.4 -20.0 L-14.3 -19.9 L-14.3 -19.7 L-14.2 -19.4 L-14.1 -19.0 L-14.0 -18.8 L-13.9 -18.4 L-13.3 -17.2 L-12.7 -16.4 L-11.6 -15.2 L-11.6 -15.2 L-10.7 -14.5 L-9.5 -13.8 L-9.4 -13.8 L-9.0 -13.6 L-8.9 -13.6 L-8.7 -13.5 L-8.5 -13.5 L-7.6 -13.1 L-7.3 -13.1 L-7.3 -13.0 L-7.1 -13.0 L-7.0 -12.9 L-6.8 -12.9 L-6.4 -12.8 L-6.1 -12.8 L-6.0 -12.7 L-5.7 -12.7 L-5.6 -12.7 L-5.2 -12.7 L-5.2 -12.6 L-4.7 -12.6 L-4.6 -12.5 L-4.3 -12.5 L-4.2 -12.4 L-4.7 -11.9 L-5.0 -11.5 L-5.3 -10.9 L-5.3 -10.8 L-5.5 -10.3 L-5.7 -9.5 L-5.8 -9.3 L-6.1 -9.2 L-6.3 -9.1 L-6.5 -9.1 L-7.1 -8.9 L-7.5 -8.9 L-7.6 -8.8 L-9.2 -8.8 L-9.2 -8.9 L-9.5 -8.9 L-9.6 -8.9 L-10.0 -9.0 L-10.3 -9.2 L-10.5 -9.2 L-10.6 -9.4 L-11.1 -9.6 L-11.6 -10.1 L-11.6 -10.1 L-12.1 -10.7 L-13.0 -12.0 L-13.7 -12.7 L-14.3 -13.1 L-15.3 -13.5 L-15.6 -13.5 L-15.6 -13.6 L-16.5 -13.6 L-16.6 -13.5 L-16.8 -13.5 L-17.1 -13.3 L-17.0 -12.9 L-16.5 -12.4 L-15.9 -12.1 L-15.0 -11.2 L-13.9 -9.5 L-13.4 -8.3 L-12.9 -7.6 L-12.1 -6.9 L-11.0 -6.3 L-10.3 -6.2 L-10.2 -6.1 L-9.8 -6.1 L-9.7 -6.0 L-9.1 -6.0 L-9.0 -6.0 L-7.8 -6.0 L-7.7 -6.0 L-6.4 -6.1 L-6.3 -6.2 L-6.0 -6.2 L-5.9 -6.3 L-5.8 -6.2 L-5.8 -4.7 L-5.7 -4.7 L-5.7 -1.7 L-6.0 -1.2 L-6.2 -1.0 L-6.4 -0.9 L-6.4 -0.9 L-6.2 -0.9 L-5.9 -0.7 L-5.7 -0.7 L-5.6 -0.7 L-5.4 -0.7 L-5.0 -0.5 L-4.7 -0.5 L-4.4 -0.4 L-4.0 -0.4 L-3.9 -0.3 L-3.1 -0.2 L-3.1 -0.1 L-2.5 -0.1 L-2.5 -0.1 L-1.8 -0.1 L-1.7 0.0 L1.7 0.0 L1.8 -0.1 L2.5 -0.1 L2.5 -0.1 L3.1 -0.1 L3.1 -0.2 L3.6 -0.2 L3.6 -0.3 L3.9 -0.3 L4.0 -0.4 L4.4 -0.4 L4.4 -0.4 L5.0 -0.5 L5.1 -0.6 L5.9 -0.7 L6.2 -0.9 L6.4 -0.9 L5.9 -1.3 L5.7 -1.7 L5.7 -9.2 L5.7 -9.3 L5.7 -9.7 L5.6 -9.8 L5.6 -10.0 L5.5 -10.1 L5.5 -10.3 L5.5 -10.4 L5.4 -10.8 L4.9 -11.6 L4.2 -12.4 L4.3 -12.5 L4.6 -12.5 L4.7 -12.6 L5.2 -12.6 L5.2 -12.7 L5.6 -12.7 L5.7 -12.7 L6.4 -12.8 L6.5 -12.9 L7.1 -12.9 L7.1 -13.0 L7.3 -13.0 L7.6 -13.2 L7.9 -13.2 L7.9 -13.2 L8.5 -13.4 L10.3 -14.2 L11.4 -15.0 L11.9 -15.5 L12.0 -15.5 L12.7 -16.2 L13.7 -18.0 L13.7 -18.1 L14.0 -18.5 L14.0 -18.6 L14.3 -19.6 L14.3 -19.8 L14.4 -19.9 L14.4 -20.1 L14.5 -20.4 L14.5 -20.7 L14.6 -20.8 L14.7 -21.8 L14.8 -21.9 L14.8 -22.8 L14.8 -22.9 L14.8 -24.4 L14.8 -24.4 L14.8 -25.1 L14.7 -25.2 L14.7 -25.5 L14.6 -25.6 L14.5 -26.2 L14.5 -26.3 L14.3 -27.1 L14.1 -27.3 L14.1 -27.4 L13.7 -28.1 L13.6 -28.3 L13.2 -28.9 L12.4 -29.9 L12.7 -30.5 L12.7 -30.7 L12.8 -31.1 L12.8 -31.4 L12.9 -31.5 L12.9 -33.5 L12.8 -33.6 L12.8 -34.0 L12.7 -34.1 L12.7 -34.7 L12.6 -34.8 L12.5 -35.2 L12.2 -35.9 L12.1 -35.9 L12.0 -36.0 L11.4 -36.0 L11.3 -35.9 L10.9 -35.9 L10.8 -35.9 L10.5 -35.9 L10.0 -35.6 L9.7 -35.6 L9.5 -35.5 L9.4 -35.5 L9.2 -35.3 L8.7 -35.2 L7.6 -34.7 L7.5 -34.5 L7.0 -34.3 L5.9 -33.6 L5.7 -33.6 L5.6 -33.7 L5.4 -33.7 L5.0 -33.8 L4.7 -33.8 L4.7 -33.9 L4.4 -33.9 L4.3 -34.0 L4.0 -34.0 L3.9 -34.0 L3.1 -34.1 L3.0 -34.2 L2.5 -34.2 L2.4 -34.3 L1.7 -34.3 L1.6 -34.3 L-1.5 -34.3 L-1.6 -34.3 L-2.3 -34.3 L-2.4 -34.2 L-3.0 -34.2 L-3.1 -34.1 L-3.5 -34.1 L-3.6 -34.0 L-3.9 -34.0 L-3.9 -34.0 L-4.3 -34.0 L-4.7 -33.8 L-4.9 -33.8 L-5.0 -33.7 L-5.8 -33.6 L-6.5 -34.0 L-6.7 -34.1 L-6.8 -34.3 L-7.1 -34.3 L-7.2 -34.5 L-8.8 -35.3 L-8.9 -35.3 L-9.5 -35.6 L-10.0 -35.6 L-10.5 -35.9 L-10.8 -35.9 L-10.9 -35.9 L-11.4 -35.9 L-11.5 -36.0 Z"/>'
        "</g>"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f"<style>{''.join(css)}</style>"
        + "".join(grid)
        + "".join(overlays)
        + "".join(mice)
        + cat
        + "</svg>"
    )


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "surmeliugur"
    out = sys.argv[2] if len(sys.argv) > 2 else "cat-grid.svg"
    svg = build_svg(fetch_cells(user))
    import os

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Yazıldı: {out} ({len(svg) // 1024} KB)")
