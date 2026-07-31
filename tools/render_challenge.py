#!/usr/bin/env python3
"""The forgery challenge: two coherence fingerprints, one lie.

The same field equation as the banner -- (D*L + kappa^2*I) tau = s -- but
solved on a POLAR lattice (rings x spokes) and rendered as a rotating
interference mandala: ring paths displaced by tau, node stars brightened by
tau, layers counter-rotating. challenge-a.svg uses the true sources;
challenge-b.svg quietly moves one source. Exact integer arithmetic throughout;
either fingerprint is judged by:

    python tools/render_challenge.py --verify assets/challenge-a.svg
    python tools/render_challenge.py --verify assets/challenge-b.svg
"""

import hashlib
import json
import math
import os
import sys

S = 600                       # square canvas
CX = CY = S // 2
SPOKES, RINGS = 48, 10
R_MIN, R_MAX = 52, 258
D_MILLI = 1000
K2_MILLI = 30
ITERS = 300
SRC = 1 << 44
DISP = 74                     # max radial displacement, px
TRUE_SOURCES = [(3, 7), (31, 4)]      # (spoke, ring)
FORGED_SOURCES = [(3, 7), (29, 5)]    # second source nudged
GOLD = "#E8B34B"
VIOLET = "#9B7BFF"
BG = "#0B0912"
META = "#5A5470"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

# integer trig tables (milli units) -- exact, shared by both fingerprints
COS = [round(1000 * math.cos(2 * math.pi * i / SPOKES)) for i in range(SPOKES)]
SIN = [round(1000 * math.sin(2 * math.pi * i / SPOKES)) for i in range(SPOKES)]


def solve(sources):
    n = SPOKES * RINGS
    idx = lambda s, r: r * SPOKES + s
    nbr = [[] for _ in range(n)]
    for r in range(RINGS):
        for s in range(SPOKES):
            nbr[idx(s, r)].append(idx((s + 1) % SPOKES, r))
            nbr[idx((s + 1) % SPOKES, r)].append(idx(s, r))
            if r + 1 < RINGS:
                nbr[idx(s, r)].append(idx(s, r + 1))
                nbr[idx(s, r + 1)].append(idx(s, r))
    src = [0] * n
    for s, r in sources:
        src[idx(s, r)] = SRC
    tau = [0] * n
    for _ in range(ITERS):
        tau = [
            (src[i] + D_MILLI * sum(tau[j] for j in nbr[i])) // (D_MILLI * len(nbr[i]) + K2_MILLI)
            for i in range(n)
        ]
    tmax = max(tau) or 1
    return tau, [t * 1000 // tmax for t in tau]


def ring_path(bright, r):
    rad0 = R_MIN + (R_MAX - R_MIN) * r // (RINGS - 1)
    pts = []
    for s in range(SPOKES):
        b = bright[r * SPOKES + s]
        rad = rad0 + (b * DISP // 1000) - DISP // 3
        pts.append((CX + rad * COS[s] // 1000, CY + rad * SIN[s] // 1000))
    d = [f"M{pts[0][0]} {pts[0][1]}"]
    for i in range(1, SPOKES + 1):
        p = pts[i % SPOKES]
        q = pts[(i + 1) % SPOKES]
        d.append(f"Q{p[0]} {p[1]} {(p[0] + q[0]) // 2} {(p[1] + q[1]) // 2}")
    return " ".join(d) + " Z"


def render(bright, field_sha, label):
    mono = "'SFMono-Regular','Cascadia Code',Consolas,monospace"
    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}" '
               f'role="img" aria-label="coherence fingerprint {label}">')
    out.append(f'<!-- RE-EXECUTABLE FIGURE. Polar solve of (D*L + kappa^2*I) tau = s, '
               f'{SPOKES}x{RINGS} ring lattice, exact integers. sha256(field)={field_sha}. '
               f'Judge me: python tools/render_challenge.py (verify mode) on assets/challenge-{label}.svg -->')
    out.append('<defs>')
    out.append(f'<radialGradient id="bg" cx="0.5" cy="0.5" r="0.72">'
               f'<stop offset="0" stop-color="#171226"/><stop offset="1" stop-color="{BG}"/></radialGradient>')
    out.append(f'<clipPath id="rc"><rect width="{S}" height="{S}" rx="24" ry="24"/></clipPath>')
    out.append('<filter id="glow" x="-60%" y="-60%" width="220%" height="220%">'
               '<feGaussianBlur stdDeviation="4"/></filter>')
    out.append('</defs>')
    out.append('<g clip-path="url(#rc)">')
    out.append(f'<rect width="{S}" height="{S}" fill="url(#bg)"/>')
    # counter-rotating ring layers
    out.append(f'<g transform="rotate(0 {CX} {CY})">'
               f'<animateTransform attributeName="transform" type="rotate" '
               f'from="0 {CX} {CY}" to="360 {CX} {CY}" dur="90000ms" repeatCount="indefinite"/>')
    for r in range(0, RINGS, 2):
        mb = sum(bright[r * SPOKES:(r + 1) * SPOKES]) // SPOKES
        lo = 90 + mb * 260 // 1000
        out.append(f'<path d="{ring_path(bright, r)}" fill="none" stroke="{GOLD}" '
                   f'stroke-width="1.4" stroke-opacity="0.{lo:03d}" filter="url(#glow)"/>')
        out.append(f'<path d="{ring_path(bright, r)}" fill="none" stroke="{GOLD}" '
                   f'stroke-width="1.2" stroke-opacity="0.{min(900, lo + 300):03d}"/>')
    out.append('</g>')
    out.append(f'<g transform="rotate(0 {CX} {CY})">'
               f'<animateTransform attributeName="transform" type="rotate" '
               f'from="360 {CX} {CY}" to="0 {CX} {CY}" dur="120000ms" repeatCount="indefinite"/>')
    for r in range(1, RINGS, 2):
        mb = sum(bright[r * SPOKES:(r + 1) * SPOKES]) // SPOKES
        lo = 90 + mb * 260 // 1000
        out.append(f'<path d="{ring_path(bright, r)}" fill="none" stroke="{VIOLET}" '
                   f'stroke-width="1.4" stroke-opacity="0.{lo:03d}" filter="url(#glow)"/>')
        out.append(f'<path d="{ring_path(bright, r)}" fill="none" stroke="{VIOLET}" '
                   f'stroke-width="1.2" stroke-opacity="0.{min(900, lo + 300):03d}"/>')
    out.append('</g>')
    # node stars, tau-bright, breathing
    stars = []
    for r in range(RINGS):
        rad0 = R_MIN + (R_MAX - R_MIN) * r // (RINGS - 1)
        for s in range(SPOKES):
            b = bright[r * SPOKES + s]
            if b < 40:
                continue
            rad = rad0 + (b * DISP // 1000) - DISP // 3
            x, y = CX + rad * COS[s] // 1000, CY + rad * SIN[s] // 1000
            op = 120 + b * 740 // 1000
            rr = 10 + b * 16 // 1000
            stars.append(f'<circle cx="{x}" cy="{y}" r="{rr // 10}.{rr % 10}" fill="#F5EFDD" '
                         f'opacity="0.{op:03d}"><animate attributeName="opacity" '
                         f'values="0.{op:03d};0.{max(60, op - 300):03d};0.{op:03d}" '
                         f'dur="{5200 + (b % 7) * 800}ms" begin="-{b * 4}ms" repeatCount="indefinite"/></circle>')
    out.append('<g>' + "".join(stars) + '</g>')
    # the pupil: field hash, dead center
    out.append(f'<circle cx="{CX}" cy="{CY}" r="34" fill="{BG}" stroke="{GOLD}" stroke-opacity="0.5"/>')
    out.append(f'<text x="{CX}" y="{CY - 2}" text-anchor="middle" font-family={mono!r} font-size="11" '
               f'fill="{GOLD}">τ-field</text>')
    out.append(f'<text x="{CX}" y="{CY + 14}" text-anchor="middle" font-family={mono!r} font-size="10" '
               f'fill="{META}">{field_sha[:8]}</text>')
    out.append(f'<text x="{S // 2}" y="{S - 16}" text-anchor="middle" font-family={mono!r} font-size="10" '
               f'fill="{META}">(D·L + κ²I)τ = s on a {SPOKES}×{RINGS} polar lattice · exact integers · '
               f'one of us is lying</text>')
    out.append('</g></svg>')
    return "\n".join(out).encode("utf-8")


def build(label, sources):
    tau, bright = solve(sources)
    sha = hashlib.sha256(",".join(map(str, tau)).encode()).hexdigest()
    return render(bright, sha, label), sha


def main():
    truth, tsha = build("a", TRUE_SOURCES)
    forged, fsha = build("b", FORGED_SOURCES)
    if "--verify" in sys.argv:
        target = sys.argv[sys.argv.index("--verify") + 1]
        given = open(target, "rb").read()
        # the true artifact must equal the TRUE field's rendering under its own label
        for label, blob in (("a", truth), ("b", forged)):
            if os.path.basename(target) == f"challenge-{label}.svg":
                expect_true = build(label, TRUE_SOURCES)[0]
                if given == expect_true:
                    print(f"VERIFIED: {target} was rendered from the TRUE field.")
                    sys.exit(0)
                print(f"FORGED: {target} does not re-derive from the true field.")
                sys.exit(1)
        print("unknown challenge file"); sys.exit(2)
    os.makedirs(ASSETS, exist_ok=True)
    for label, blob in (("a", truth), ("b", forged)):
        p = os.path.join(ASSETS, f"challenge-{label}.svg")
        with open(p, "wb") as f:
            f.write(blob)
        print(f"wrote {os.path.relpath(p, ROOT)}  sha256={hashlib.sha256(blob).hexdigest()[:16]}...")


if __name__ == "__main__":
    main()
