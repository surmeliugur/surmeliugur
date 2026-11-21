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
LEAD, TAIL = 1.0, 2.0  # başlangıç bekleme / bitiş (eve dönüş + duraklama)

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

    events = [(w, r) for _, w, r, lv in items if lv > 0]
    n = len(events)
    D = LEAD + n * SLOT + TAIL
    home = (PAD_L / 2, PAD_T + 3.5 * PITCH + 14)

    css = [
        ":root{--c0:%s;--c1:%s;--c2:%s;--c3:%s;--c4:%s;--cat:#1f2328;--mouse:#8b949e}"
        % tuple(LEVEL_LIGHT),
        "@media(prefers-color-scheme:dark){:root{--c0:%s;--c1:%s;--c2:%s;--c3:%s;--c4:%s;"
        "--cat:#f0f6fc;--mouse:#9198a1}}" % tuple(LEVEL_DARK),
        ".cat,.m{transform-origin:0 0}",
    ]

    # --- kedi anahtar kareleri ---
    kf = [(0.0, home[0], home[1], 1.0)]
    prev = home
    for i, (w, r) in enumerate(events):
        cx, cy = center(w, r)
        cy += 6
        s = LEAD + i * SLOT
        kf.append((s, prev[0], prev[1], 1.0))
        kf.append((s + 0.4 * SLOT, (prev[0] + cx) / 2, min(prev[1], cy) - 24, 1.0))
        kf.append((s + 0.62 * SLOT, cx, cy, 0.82))   # patiyle bas (ezilme)
        kf.append((s + 0.78 * SLOT, cx, cy, 1.0))
        prev = (cx, cy)
    end = LEAD + n * SLOT
    kf.append((end, prev[0], prev[1], 1.0))
    kf.append((end + 1.0, home[0], home[1], 1.0))
    kf.append((D, home[0], home[1], 1.0))
    css.append("@keyframes cat{")
    for t, x, y, sy in kf:
        css.append(
            f"{pct(t, D)}{{transform:translate({x:.1f}px,{y:.1f}px) scale(1,{sy})}}"
        )
    css.append("}")
    css.append(f".cat{{animation:cat {D:.2f}s ease-in-out infinite}}")

    # --- fare anahtar kareleri (her kare için ayrı) ---
    mice = []
    for i, (w, r) in enumerate(events):
        s = LEAD + i * SLOT
        css.append(
            f"@keyframes m{i}{{0%,{pct(s, D)}{{transform:scale(0)}}"
            f"{pct(s + 0.2 * SLOT, D)}{{transform:scale(1)}}"
            f"{pct(s + 0.6 * SLOT, D)}{{transform:scale(1)}}"
            f"{pct(s + 0.66 * SLOT, D)}{{transform:scale(1.4,.2)}}"
            f"{pct(s + 0.8 * SLOT, D)},100%{{transform:scale(0)}}}}"
        )
        css.append(f".m{i}{{animation:m{i} {D:.2f}s linear infinite}}")
        cx, cy = center(w, r)
        mice.append(
            f'<g transform="translate({cx:.1f},{cy + 3:.1f})"><g class="m m{i}">'
            f'<ellipse cx="0" cy="-3" rx="4.2" ry="3" fill="var(--mouse)"/>'
            f'<circle cx="-3" cy="-6" r="1.8" fill="var(--mouse)"/>'
            f'<circle cx="3" cy="-6" r="1.8" fill="var(--mouse)"/>'
            f'<path d="M4 -2 q4 0 4 -4" stroke="var(--mouse)" stroke-width="1" fill="none"/>'
            f"</g></g>"
        )

    # --- ızgara ---
    grid = []
    for _, w, r, lv in items:
        x, y = PAD_L + w * PITCH, PAD_T + r * PITCH
        grid.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="var(--c{lv})"/>'
        )

    # --- Octocat tarzı kedi (arkası dönük): ayak tabanı orijinde, ~36px boyunda ---
    cat = (
        '<g class="cat" fill="var(--cat)">'
        '<path d="M9 -5 C21 -3 24 -17 17 -24 C15 -26 12 -25 13 -23 C17 -18 14 -11 8 -11 Z"/>'  # kıvrık dokunaç/kuyruk
        '<path d="M-2 -1 C-4 2 -8 2 -9 -1 L-6 -4 Z"/><path d="M2 -1 C4 2 8 2 9 -1 L6 -4 Z"/>'  # arka patiler
        '<ellipse cx="0" cy="-10" rx="11" ry="9"/>'  # gövde
        '<circle cx="0" cy="-23" r="10.5"/>'  # kafa
        '<path d="M-10 -26 L-9.5 -38 L-1 -31 Z"/><path d="M10 -26 L9.5 -38 L1 -31 Z"/>'  # kulaklar
        "</g>"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f"<style>{''.join(css)}</style>"
        + "".join(grid)
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
