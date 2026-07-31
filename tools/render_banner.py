#!/usr/bin/env python3
"""Josh Philbrick's profile banner as a re-executable figure (v3, aurora).

The backdrop is the solution of the coherence field equation

    (D*L + kappa^2*I) tau = s

solved over a lattice in EXACT INTEGER arithmetic, rendered as layered aurora
bands and rolling ribbons whose amplitudes, speeds, weights and glow all come
from the field. Every byte is a pure function of the parameters below; CI
re-derives the artifact on every push and fails on one byte of drift.

Usage:
    python tools/render_banner.py           # write assets/banner.svg + RECEIPT.json
    python tools/render_banner.py --check   # re-derive and byte-compare
"""

import hashlib
import json
import os
import sys

# ---------------------------------------------------------------- parameters
W, H = 1200, 360
COLS, ROWS = 40, 12
D_MILLI = 1000
K2_MILLI = 45
ITERS = 300
SRC = 1 << 44
SEED = 0x1A0501
SOURCES = [(0.70, 0.35), (0.90, 0.62), (0.58, 0.82)]
N_BANDS = 4                  # filled aurora layers
N_WAVES = 7                  # crisp ribbons on top
WAVE_PTS = 30
BASE_AMP = 8
FIELD_AMP = 40
PULSE_MS = 9000

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

BG = "#070E1C"
META = "#46607A"
GRAD = ("#155E7A", "#3FB6E0", "#8FE3CF")


def lcg(seed):
    s = seed
    while True:
        s = (s * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        yield s >> 33


def solve_field():
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
    c = min(COLS - 1, x_milli * COLS // 1000)
    r = min(ROWS - 1, y_milli * ROWS // 1000)
    return bright[r * COLS + c]


def wave_pts(bright, y0, k, base_phase, phase_shift, amp_scale_milli=1000):
    pts = []
    for i in range(WAVE_PTS + 1):
        x = i * W // WAVE_PTS
        b = field_at(bright, x * 1000 // W, y0 * 1000 // H)
        amp = (BASE_AMP + b * FIELD_AMP // 1000) * amp_scale_milli // 1000
        t = (i * 250 + base_phase + phase_shift + k * 137) % 1000
        tri = (2 * t if t < 500 else 2 * (1000 - t)) - 500
        pts.append((x, y0 + amp * tri // 500))
    return pts


def smooth(pts):
    d = [f"M{pts[0][0]} {pts[0][1]}"]
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) // 2, (pts[i][1] + pts[i + 1][1]) // 2
        d.append(f"Q{pts[i][0]} {pts[i][1]} {mx} {my}")
    d.append(f"L{pts[-1][0]} {pts[-1][1]}")
    return " ".join(d)


def ribbon_frames(bright, y0, k, base_phase, amp_scale=1000):
    frames = [smooth(wave_pts(bright, y0, k, base_phase, ph, amp_scale))
              for ph in (0, 250, 500, 750)]
    frames.append(frames[0])
    return frames


def band_frames(bright, y0, k, base_phase):
    frames = []
    for ph in (0, 250, 500, 750):
        pts = wave_pts(bright, y0, k, base_phase, ph, 1400)
        frames.append(smooth(pts) + f" L{W} {H} L0 {H} Z")
    frames.append(frames[0])
    return frames


def mean_bright(bright, y0):
    return sum(field_at(bright, i * 1000 // WAVE_PTS, y0 * 1000 // H)
               for i in range(WAVE_PTS + 1)) // (WAVE_PTS + 1)


def render(bright, field_sha):
    fonts = "'Inter','Segoe UI',system-ui,-apple-system,sans-serif"
    mono = "'SFMono-Regular','Cascadia Code',Consolas,monospace"
    rnd = lcg(SEED ^ 0xBEE5)
    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
               f'width="{W}" height="{H}" role="img" '
               f'aria-label="Josh Philbrick - creator, systems thinker, and founder of Coherence Energy Labs">')
    out.append(f'<!-- RE-EXECUTABLE FIGURE. Aurora + ribbon amplitudes = solution of '
               f'(D*L + kappa^2*I) tau = s on a {COLS}x{ROWS} lattice, exact integer arithmetic. '
               f'params: D_milli={D_MILLI} k2_milli={K2_MILLI} iters={ITERS} seed={SEED:#x} '
               f'src={SRC:#x} bands={N_BANDS} waves={N_WAVES}. sha256(field)={field_sha}. '
               f'Re-derive: python tools/render_banner.py -->')
    out.append('<defs>')
    out.append(f'<radialGradient id="vig" cx="0.72" cy="0.5" r="0.9">'
               f'<stop offset="0" stop-color="#0D2135"/><stop offset="1" stop-color="{BG}"/></radialGradient>')
    out.append(f'<linearGradient id="w" x1="0" y1="0" x2="1" y2="0">'
               f'<stop offset="0" stop-color="{GRAD[0]}">'
               f'<animate attributeName="stop-color" values="{GRAD[0]};{GRAD[1]};{GRAD[0]}" dur="11000ms" repeatCount="indefinite"/></stop>'
               f'<stop offset="0.6" stop-color="{GRAD[1]}">'
               f'<animate attributeName="stop-color" values="{GRAD[1]};{GRAD[2]};{GRAD[1]}" dur="11000ms" repeatCount="indefinite"/></stop>'
               f'<stop offset="1" stop-color="{GRAD[2]}"/></linearGradient>')
    out.append(f'<linearGradient id="fillw" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0" stop-color="{GRAD[1]}" stop-opacity="0.16"/>'
               f'<stop offset="1" stop-color="{GRAD[0]}" stop-opacity="0"/></linearGradient>')
    out.append('<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
               '<feGaussianBlur stdDeviation="6"/></filter>')
    out.append('<filter id="glow" x="-150%" y="-150%" width="400%" height="400%">'
               '<feGaussianBlur stdDeviation="3"/></filter>')
    out.append(f'<linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0">'
               f'<stop offset="0" stop-color="{BG}" stop-opacity="0.82"/>'
               f'<stop offset="0.72" stop-color="{BG}" stop-opacity="0.55"/>'
               f'<stop offset="1" stop-color="{BG}" stop-opacity="0"/></linearGradient>')
    out.append(f'<linearGradient id="name" x1="0" y1="0" x2="1" y2="0">'
               f'<stop offset="0" stop-color="#FFFFFF"/>'
               f'<stop offset="0.5" stop-color="#BFEFFF">'
               f'<animate attributeName="offset" values="0.2;0.8;0.2" dur="8000ms" repeatCount="indefinite"/></stop>'
               f'<stop offset="1" stop-color="#E8FBFF"/></linearGradient>')
    out.append(f'<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0">'
               f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
               f'<stop offset="0.5" stop-color="#CFF4FF" stop-opacity="0.07"/>'
               f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>')
    out.append(f'<clipPath id="rc"><rect width="{W}" height="{H}" rx="26" ry="26"/></clipPath>')
    out.append('</defs>')
    out.append('<g clip-path="url(#rc)">')
    out.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    # deterministic starfield, twinkling
    srnd = lcg(SEED ^ 0x57A125)
    stars = []
    for _ in range(46):
        sx = next(srnd) % W
        sy = next(srnd) % H
        so = 200 + next(srnd) % 500
        sd = 2600 + next(srnd) % 5200
        sb = next(srnd) % sd
        stars.append(f'<circle cx="{sx}" cy="{sy}" r="1" fill="#BFE8F5" opacity="0.{so:03d}">'
                     f'<animate attributeName="opacity" values="0.{so:03d};0.050;0.{so:03d}" '
                     f'dur="{sd}ms" begin="-{sb}ms" repeatCount="indefinite"/></circle>')
    out.append('<g>' + "".join(stars) + '</g>')
    # --- soft aurora bands (filled, blurred, morphing)
    out.append('<g filter="url(#soft)">')
    for k in range(N_BANDS):
        y0 = (k + 1) * H // (N_BANDS + 1) + 20
        base_phase = next(rnd) % 1000
        frames = band_frames(bright, y0, k, base_phase)
        mb = mean_bright(bright, y0)
        dur = 21000 - mb * 9000 // 1000
        out.append(f'<path d="{frames[0]}" fill="url(#fillw)">'
                   f'<animate attributeName="d" values="{";".join(frames)}" dur="{dur}ms" '
                   f'begin="-{(base_phase * dur) // 1000}ms" repeatCount="indefinite" calcMode="linear"/></path>')
    out.append('</g>')
    # --- neon under-glow + crisp rolling ribbons, parallax from the field
    out.append('<g fill="none" stroke="url(#w)" stroke-linecap="round">')
    particles = []
    neon = []
    for k in range(N_WAVES):
        y0 = (k + 1) * H // (N_WAVES + 1)
        base_phase = next(rnd) % 1000
        frames = ribbon_frames(bright, y0, k, base_phase)
        mb = mean_bright(bright, y0)
        lo = 60 + mb * 170 // 1000
        hi = 170 + mb * 610 // 1000
        dur = 15000 - mb * 8500 // 1000
        width_tenths = 12 + mb * 20 // 1000
        begin = (base_phase * dur) // 1000
        neon.append(
            f'<path d="{frames[0]}" stroke-opacity="0.{(lo // 3):03d}" '
            f'stroke-width="{(width_tenths + 46) // 10}.{(width_tenths + 46) % 10}" filter="url(#glow)">'
            f'<animate attributeName="d" values="{";".join(frames)}" '
            f'dur="{dur}ms" begin="-{begin}ms" repeatCount="indefinite" calcMode="linear"/></path>')
        out.append(
            f'<path d="{frames[0]}" stroke-opacity="0.{lo:03d}" '
            f'stroke-width="{width_tenths // 10}.{width_tenths % 10}">'
            f'<animate attributeName="d" values="{";".join(frames)}" '
            f'dur="{dur}ms" begin="-{begin}ms" repeatCount="indefinite" calcMode="linear"/>'
            f'<animate attributeName="stroke-opacity" values="0.{lo:03d};0.{hi:03d};0.{lo:03d}" '
            f'dur="{PULSE_MS}ms" begin="-{begin}ms" repeatCount="indefinite"/></path>')
        if k % 2 == 1:
            r_t = 13 + mb * 15 // 1000
            pdur = 20000 - mb * 9000 // 1000
            pb = (base_phase * pdur) // 1000
            particles.append(
                f'<g><circle r="{(r_t + 22) // 10}.{(r_t + 22) % 10}" fill="{GRAD[2]}" '
                f'fill-opacity="0.35" filter="url(#glow)">'
                f'<animateMotion path="{frames[0]}" dur="{pdur}ms" begin="-{pb}ms" repeatCount="indefinite"/></circle>'
                f'<circle r="{r_t // 10}.{r_t % 10}" fill="#EAFBF5" fill-opacity="0.9">'
                f'<animateMotion path="{frames[0]}" dur="{pdur}ms" begin="-{pb}ms" repeatCount="indefinite"/>'
                f'<animate attributeName="fill-opacity" values="0;0.9;0.9;0" keyTimes="0;0.07;0.93;1" '
                f'dur="{pdur}ms" begin="-{pb}ms" repeatCount="indefinite"/></circle></g>')
    out.append('</g>')
    out.append('<g fill="none" stroke="url(#w)" stroke-linecap="round">' + "".join(neon) + '</g>')
    out.append('<g>' + "".join(particles) + '</g>')
    # readability scrim: gradient fade, no hard seam
    out.append(f'<rect x="0" y="0" width="860" height="{H}" fill="url(#scrim)"/>')
    # passing light sheen, every 9s
    out.append(f'<rect x="-420" y="-40" width="340" height="{H + 80}" fill="url(#sheen)" '
               f'transform="skewX(-18)">'
               f'<animateTransform attributeName="transform" type="translate" additive="sum" '
               f'values="0 0; {W + 900} 0" dur="9000ms" repeatCount="indefinite"/></rect>')
    # --- the text stack, same layout as the original banner
    out.append(f'<text x="72" y="82" fill="#80e7ff" font-family={fonts!r} font-size="16" '
               f'font-weight="700" letter-spacing="3.2">CREATOR&#160;&#160;·&#160;&#160;SYSTEMS THINKER&#160;&#160;·&#160;&#160;FOUNDER</text>')
    out.append(f'<text x="68" y="154" fill="url(#name)" font-family={fonts!r} font-size="58" '
               f'font-weight="780" letter-spacing="-1.8">JOSH PHILBRICK</text>')
    out.append(f'<text x="72" y="205" fill="#c7d4ee" font-family={fonts!r} font-size="22" '
               f'font-weight="430">Founder of Coherence Energy Labs</text>')
    out.append(f'<text x="72" y="258" fill="#eef5ff" font-family={fonts!r} font-size="23" '
               f'font-weight="560">Building systems for questions most people</text>')
    out.append(f'<text x="72" y="290" fill="#eef5ff" font-family={fonts!r} font-size="23" '
               f'font-weight="560">are told are too large to ask.</text>')
    out.append(f'<text x="72" y="330" fill="#7f90ad" font-family={fonts!r} font-size="14" '
               f'font-weight="500" letter-spacing="1.4">PHYSICS&#160;&#160;·&#160;&#160;COMPUTATION&#160;&#160;·&#160;&#160;BIOLOGY&#160;&#160;·&#160;&#160;INTELLIGENCE</text>')
    out.append(f'<text x="{W - 20}" y="{H - 14}" text-anchor="end" font-family={mono!r} '
               f'font-size="11" fill="{META}">(D·L + κ²I)τ = s · exact integers · '
               f'sha256(field) = {field_sha[:12]}… · re-derive: tools/render_banner.py</text>')
    out.append('</g>')
    out.append('</svg>')
    return "\n".join(out).encode("utf-8")


def main():
    check = "--check" in sys.argv
    tau, bright = solve_field()
    field_sha = hashlib.sha256(",".join(map(str, tau)).encode()).hexdigest()
    svg = render(bright, field_sha)
    receipt = {
        "artifact": "profile banner v3 (animated SVG: aurora bands + rolling ribbons + photons)",
        "equation": "(D*L + kappa^2*I) tau = s",
        "arithmetic": "exact integer (python int), no floats in field or geometry",
        "params": {"W": W, "H": H, "COLS": COLS, "ROWS": ROWS, "D_milli": D_MILLI,
                    "kappa2_milli": K2_MILLI, "iters": ITERS, "seed": hex(SEED),
                    "source_strength": hex(SRC), "sources": SOURCES,
                    "n_bands": N_BANDS, "n_waves": N_WAVES, "wave_pts": WAVE_PTS,
                    "base_amp": BASE_AMP, "field_amp": FIELD_AMP, "pulse_ms": PULSE_MS},
        "sha256_field": field_sha,
        "sha256_svg": hashlib.sha256(svg).hexdigest(),
        "re_derive": "python tools/render_banner.py --check",
    }
    rec_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    targets = {os.path.join(ASSETS, "banner.svg"): svg,
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
