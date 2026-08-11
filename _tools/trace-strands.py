"""
Trace the internal strands of the mark, for the Life chapter of /mark.

The page annotates the strand fan inside the lower lobe with fine lines. Those
lines have to sit on the grooves, and guessing them by eye lands them 30-60px
off in a 2000px render — close enough to look like a mistake rather than a
drawing. So they are measured: the grooves are darker than the surface around
them, and this walks down each column of the render finding those dark troughs,
links them into continuous tracks, and fits a smooth path to each.

    python _tools/trace-strands.py

Prints one SVG <path> per groove it finds, numbered, alongside a proof sheet
that draws each one on the render in its own colour. Not every groove is a
strand — the ribbon's outer edge and its inner fold are troughs too, and no
rule separated them reliably (the topmost strand runs as close to the
silhouette as the edge does). So the numbering is the point: look at the proof
sheet, take the paths that are strands, paste those.

At the time of writing that is tracks 2, 3, 4 and 5; tracks 0 and 1 are the
outer edge and the inner fold.

Re-run after replacing img/Logo.png. The coordinates live in the render's own
2000x1420 space and do not survive a re-render or a re-crop.

Requires: pillow, numpy.
"""
import numpy as np
from PIL import Image, ImageDraw

SRC = "img/mark-light-2000.webp"       # the silver cut: bright surface, dark grooves
REGION = (1040, 700, 1910, 1270)       # the lower-right fan, in render coordinates
MIN_TRACK = 200                        # a groove shorter than this is a shading artefact
MAX_STEP = 16                          # how far a groove may move between columns
FLOOR = 0.055                          # how much darker than its surroundings a groove is
DEBUG = "_tools/strand-proof.png"      # proof sheet; _tools/ is never deployed


def troughs(col, floor=FLOOR):
    """Local minima deep enough to be a groove rather than shading.

    The grooves are shallow — a few percent of luminance — so the column is
    smoothed first, or every speck of render noise reads as a minimum."""
    s = np.convolve(col, np.ones(7) / 7.0, mode="same")
    out = []
    for i in range(4, len(s) - 4):
        v = s[i]
        if v <= s[i - 1] and v <= s[i + 1] and v < s[i - 3] and v < s[i + 3]:
            lo, hi = max(0, i - 30), min(len(s), i + 31)
            if (s[lo:hi].max() - v) > floor:
                out.append(i)
    return out


def main():
    x0, y0, x1, y1 = REGION
    im = Image.open(SRC).convert("RGBA")
    a = np.asarray(im.getchannel("A"), float) / 255.0
    g = np.asarray(im.convert("L"), float) / 255.0
    g = np.where(a > 0.78, g, 1.0)          # off the object is "no groove"
    band = g[y0:y1, x0:x1]

    # Column-wise trough detection, then link nearest troughs into tracks.
    tracks = []
    live = []
    for xi in range(band.shape[1]):
        found = troughs(band[:, xi])
        used = set()
        nxt = []
        for tr in live:
            best, bd = None, MAX_STEP + 1
            for yi in found:
                if yi in used:
                    continue
                d = abs(yi - tr[-1][1])
                if d < bd:
                    best, bd = yi, d
            if best is None:
                if len(tr) >= MIN_TRACK:
                    tracks.append(tr)
                continue
            used.add(best)
            tr.append((xi, best))
            nxt.append(tr)
        for yi in found:
            if yi not in used:
                nxt.append([(xi, yi)])
        live = nxt
    for tr in live:
        if len(tr) >= MIN_TRACK:
            tracks.append(tr)

    tracks.sort(key=lambda t: -len(t))
    print("# %d tracks over %dpx" % (len(tracks), MIN_TRACK))

    # Every trough in this region is printed, including the ones that are the
    # ribbon's own folded edge rather than a strand. Telling those apart by
    # rule turned out to be guesswork — the topmost strand runs as close to the
    # silhouette as the edge groove does — so the proof sheet numbers them and
    # a person picks. That choice only has to be made when the render changes.
    dbg = Image.open(SRC).convert("RGBA")
    flat = Image.new("RGB", dbg.size, (18, 20, 23))
    flat.paste(dbg, (0, 0), dbg)
    px = flat.load()
    ink = [(255, 70, 70), (70, 190, 255), (120, 230, 120), (255, 190, 60),
           (220, 120, 255), (255, 255, 255), (255, 120, 170), (140, 255, 230)]
    for i, t in enumerate(tracks):
        c = ink[i % len(ink)]
        for (xi, yi) in t:
            for k in (-1, 0, 1):
                px[xi + x0, min(flat.size[1] - 1, yi + y0 + k)] = c
    draw = ImageDraw.Draw(flat)
    for i, t in enumerate(tracks):
        mx, my = t[len(t) // 2]
        draw.text((mx + x0, my + y0 - 26), str(i), fill=ink[i % len(ink)])
    flat.crop((x0 - 90, y0 - 90, x1 + 90, y1 + 90)).save(DEBUG)

    for i, t in enumerate(tracks):
        print("#   [%d] %-9s len %4d  x %4d..%4d  y %4d..%4d"
              % (i, ink[i % len(ink)][0] and "", len(t), t[0][0] + x0, t[-1][0] + x0,
                 min(p[1] for p in t) + y0, max(p[1] for p in t) + y0))
    print("#\n# proof sheet: %s — each track numbered in its own colour" % DEBUG)

    print("\n<!-- generated by _tools/trace-strands.py — do not edit by hand -->")
    for idx, t in enumerate(tracks):
        pts = [(p[0] + x0, p[1] + y0) for p in t]
        # Trim the ends: a groove fades out rather than stopping, and the last
        # few samples wander into the shading around it.
        cut = max(6, len(pts) // 22)
        pts = pts[cut:-cut]
        # Smooth, then sample four points and fit one cubic through them.
        ys = np.convolve([p[1] for p in pts], np.ones(41) / 41.0, mode="same")
        ys[:20] = pts[20][1]
        ys[-20:] = pts[-20][1]
        n = len(pts)
        p0 = (pts[0][0], ys[0])
        p3 = (pts[-1][0], ys[-1])
        t1, t2 = pts[n // 3][0], pts[2 * n // 3][0]
        y1_, y2_ = ys[n // 3], ys[2 * n // 3]
        # Solve the two control points that put the curve through the thirds.
        c1 = ((18 * t1 - 9 * t2 - 5 * p0[0] + 2 * p3[0]) / 6.0,
              (18 * y1_ - 9 * y2_ - 5 * p0[1] + 2 * p3[1]) / 6.0)
        c2 = ((-9 * t1 + 18 * t2 + 2 * p0[0] - 5 * p3[0]) / 6.0,
              (-9 * y1_ + 18 * y2_ + 2 * p0[1] - 5 * p3[1]) / 6.0)
        print('<path d="M%d %d C%d %d %d %d %d %d" />  <!-- [%d] -->' % (
            p0[0], p0[1], c1[0], c1[1], c2[0], c2[1], p3[0], p3[1], idx))


if __name__ == "__main__":
    main()
