#!/usr/bin/env python3
"""Josh Philbrick's profile banner as a re-executable figure.

Same discipline as the Coherence Energy Labs org banner: the backdrop is the
solution of the coherence field equation

    (D*L + kappa^2*I) tau = s

solved over a lattice in EXACT INTEGER arithmetic, then rendered as flowing
wave ribbons whose amplitude envelope IS the field (the glow sits where tau is
hot). Every byte is a pure function of the parameters below; CI re-derives the
artifact on every push and fails on one byte of drift.

Usage:
    python tools/render_banner.py           # write assets/profile-banner.svg + RECEIPT.json
    python tools/render_banner.py --check   # re-derive and byte-compare
"""

import hashlib
import json
import os
import sys

# ---------------------------------------------------------------- parameters
W, H = 1200, 360
COLS, ROWS = 40, 12          # field lattice resolution
D_MILLI = 1000
K2_MILLI = 45
ITERS = 300
SRC = 1 << 44
SEED = 0x1A0501
SOURCES = [(0.70, 0.35), (0.90, 0.62), (0.58, 0.82)]   # glow right of the text
N_WAVES = 9                  # ribbon count
WAVE_PTS = 30                # samples per ribbon
BASE_AMP = 6                 # px, amplitude floor
FIELD_AMP = 34               # px, amplitude at tau max
PULSE_MS = 9000

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

BG = "#081020"
META = "#46607A"
GRAD = ("#1E6E8C", "#4FC3E8", "#9FE8D8")   # deep teal -> ice blue -> mint


def lcg(seed):
    s = seed
    while True:
        s = (s * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        yield s >> 33


def solve_field():
    """Screened field on a COLS x ROWS grid, exact integers. Returns bright 0..1000."""
    n = COLS * ROWS
    idx = lambda r, c: r * COLS + c
    nbr = [[] for _ in range(n)]
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < ROWS and 0 <= cc < COLS:
                    nbr[idx(r, c)].append(idx(rr, cc))
                    nbr[idx(rr, cc)].append(idx(r, c))
    s = [0] * n
    for fx, fy in SOURCES:
        c = min(COLS - 1, int(fx * COLS))
        r = min(ROWS - 1, int(fy * ROWS))
        s[idx(r, c)] = SRC
    tau = [0] * n
    for _ in range(ITERS):
        tau = [
            (s[i] + D_MILLI * sum(tau[j] for j in nbr[i])) // (D_MILLI * len(nbr[i]) + K2_MILLI)
            for i in range(n)
        ]
    tmax = max(tau) or 1
    return tau, [t * 1000 // tmax for t in tau]


def field_at(bright, x_milli, y_milli):
    """Nearest-cell brightness for fractional position (integer milli units)."""
    c = min(COLS - 1, x_milli * COLS // 1000)
    r = min(ROWS - 1, y_milli * ROWS // 1000)
    return bright[r * COLS + c]


def wave_path(bright, k, rnd):
    """One ribbon: smoothed through integer sample points; amplitude = field."""
    y0 = (k + 1) * H // (N_WAVES + 1)
    phase = next(rnd) % 1000
    pts = []
    for i in range(WAVE_PTS + 1):
        x = i * W // WAVE_PTS
        b = field_at(bright, x * 1000 // W, y0 * 1000 // H)
        amp = BASE_AMP + b * FIELD_AMP // 1000
        # deterministic integer "sine": triangle wave folded smooth by Q-curves
        t = (i * 250 + phase + k * 137) % 1000          # position in cycle
        tri = (2 * t if t < 500 else 2 * (1000 - t)) - 500   # -500..500
        y = y0 + amp * tri // 500
        pts.append((x, y))
    d = [f"M{pts[0][0]} {pts[0][1]}"]
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) // 2, (pts[i][1] + pts[i + 1][1]) // 2
        d.append(f"Q{pts[i][0]} {pts[i][1]} {mx} {my}")
    d.append(f"L{pts[-1][0]} {pts[-1][1]}")
    mean_b = sum(field_at(bright, p[0] * 1000 // W, y0 * 1000 // H) for p in pts) // len(pts)
    return " ".join(d), mean_b


def render(bright, field_sha):
    fonts = "'Inter','Segoe UI',system-ui,-apple-system,sans-serif"
    mono = "'SFMono-Regular','Cascadia Code',Consolas,monospace"
    rnd = lcg(SEED ^ 0xBEE5)
    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
               f'width="{W}" height="{H}" role="img" '
               f'aria-label="Josh Philbrick - creator, systems thinker, and founder of Coherence Energy Labs">')
    out.append(f'<!-- RE-EXECUTABLE FIGURE. Wave amplitudes = solution of (D*L + kappa^2*I) tau = s '
               f'on a {COLS}x{ROWS} lattice, exact integer arithmetic. params: D_milli={D_MILLI} '
               f'k2_milli={K2_MILLI} iters={ITERS} seed={SEED:#x} src={SRC:#x} waves={N_WAVES}. '
               f'sha256(field)={field_sha}. Re-derive: python tools/render_banner.py -->')
    out.append('<defs>')
    out.append(f'<linearGradient id="w" x1="0" y1="0" x2="1" y2="0">'
               f'<stop offset="0" stop-color="{GRAD[0]}"/>'
               f'<stop offset="0.62" stop-color="{GRAD[1]}"/>'
               f'<stop offset="1" stop-color="{GRAD[2]}"/></linearGradient>')
    out.append('</defs>')
    out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    # --- the field, as breathing wave ribbons
    out.append('<g fill="none" stroke="url(#w)" stroke-width="2" stroke-linecap="round">')
    for k in range(N_WAVES):
        d, mean_b = wave_path(bright, k, rnd)
        lo = 50 + mean_b * 180 // 1000            # opacity floor  .050...230
        hi = 140 + mean_b * 560 // 1000           # opacity peak   .140...700
        begin = mean_b * PULSE_MS // 1000
        drift = 4 + mean_b * 8 // 1000            # vertical breath, px
        out.append(
            f'<path d="{d}" stroke-opacity="0.{lo:03d}">'
            f'<animate attributeName="stroke-opacity" values="0.{lo:03d};0.{hi:03d};0.{lo:03d}" '
            f'dur="{PULSE_MS}ms" begin="-{begin}ms" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0; 0 -{drift}; 0 0" dur="{PULSE_MS}ms" begin="-{begin}ms" '
            f'repeatCount="indefinite"/></path>')
    out.append('</g>')
    # readability scrim behind the left text stack
    out.append(f'<rect x="0" y="0" width="740" height="{H}" fill="{BG}" fill-opacity="0.60"/>')
    # --- the original text stack, same layout as the hand-drawn banner
    out.append(f'<text x="72" y="82" fill="#80e7ff" font-family={fonts!r} font-size="16" '
               f'font-weight="700" letter-spacing="3.2">CREATOR&#160;&#160;·&#160;&#160;SYSTEMS THINKER&#160;&#160;·&#160;&#160;FOUNDER</text>')
    out.append(f'<text x="68" y="154" fill="#ffffff" font-family={fonts!r} font-size="58" '
               f'font-weight="780" letter-spacing="-1.8">JOSH PHILBRICK</text>')
    out.append(f'<text x="72" y="205" fill="#c7d4ee" font-family={fonts!r} font-size="22" '
               f'font-weight="430">Founder of Coherence Energy Labs</text>')
    out.append(f'<text x="72" y="258" fill="#eef5ff" font-family={fonts!r} font-size="23" '
               f'font-weight="560">Building systems for questions most people</text>')
    out.append(f'<text x="72" y="290" fill="#eef5ff" font-family={fonts!r} font-size="23" '
               f'font-weight="560">are told are too large to ask.</text>')
    out.append(f'<text x="72" y="330" fill="#7f90ad" font-family={fonts!r} font-size="14" '
               f'font-weight="500" letter-spacing="1.4">PHYSICS&#160;&#160;·&#160;&#160;COMPUTATION&#160;&#160;·&#160;&#160;BIOLOGY&#160;&#160;·&#160;&#160;INTELLIGENCE</text>')
    # --- the receipt, printed on the artifact
    out.append(f'<text x="{W - 20}" y="{H - 14}" text-anchor="end" font-family={mono!r} '
               f'font-size="11" fill="{META}">(D·L + κ²I)τ = s · exact integers · '
               f'sha256(field) = {field_sha[:12]}… · re-derive: tools/render_banner.py</text>')
    out.append('</svg>')
    return "\n".join(out).encode("utf-8")


def main():
    check = "--check" in sys.argv
    tau, bright = solve_field()
    field_sha = hashlib.sha256(",".join(map(str, tau)).encode()).hexdigest()
    svg = render(bright, field_sha)
    receipt = {
        "artifact": "profile banner (animated SVG, wave-ribbon rendering)",
        "equation": "(D*L + kappa^2*I) tau = s",
        "arithmetic": "exact integer (python int), no floats in field or geometry",
        "params": {"W": W, "H": H, "COLS": COLS, "ROWS": ROWS, "D_milli": D_MILLI,
                    "kappa2_milli": K2_MILLI, "iters": ITERS, "seed": hex(SEED),
                    "source_strength": hex(SRC), "sources": SOURCES,
                    "n_waves": N_WAVES, "wave_pts": WAVE_PTS,
                    "base_amp": BASE_AMP, "field_amp": FIELD_AMP, "pulse_ms": PULSE_MS},
        "sha256_field": field_sha,
        "sha256_svg": hashlib.sha256(svg).hexdigest(),
        "re_derive": "python tools/render_banner.py --check",
    }
    rec_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    targets = {os.path.join(ASSETS, "profile-banner.svg"): svg,
               os.path.join(ASSETS, "RECEIPT.json"): rec_bytes}
    if check:
        bad = [os.path.relpath(p, ROOT) for p, want in targets.items()
               if not (os.path.exists(p) and open(p, "rb").read() == want)]
        if bad:
            print(f"DRIFT: {', '.join(bad)} do not match re-derivation.")
            sys.exit(1)
        print(f"OK: banner re-derives byte-identically. sha256(field)={field_sha[:16]}...")
        return
    os.makedirs(ASSETS, exist_ok=True)
    for p, data in targets.items():
        with open(p, "wb") as f:
            f.write(data)
        print(f"wrote {os.path.relpath(p, ROOT)}  sha256={hashlib.sha256(data).hexdigest()[:16]}...")


if __name__ == "__main__":
    main()
