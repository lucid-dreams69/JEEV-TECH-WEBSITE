"""
JEEV TECH — brand asset build.

Sources live in the repo but are never served (see .vercelignore):
  img/Logo.png       7200x5400 RGBA render of the loop mark, transparent.
  img/Text logo.png  7200x5400 RGBA of the JEEV TECH wordmark, flat black.

Everything the site actually loads is generated from those two files by this
script. Nothing below is hand-edited; re-run after replacing a source.

    python _tools/build-brand-assets.py

Requires: pillow, numpy, potracer.

Two things worth knowing before changing the tracing:

  - potracer's Bitmap.__init__ calls self.invert() unconditionally, so the mask
    handed to it has to be inverted first. Pass the mask the obvious way round
    and the trace comes back as the background with the letters knocked out of
    it, which still renders — as a filled slab.
  - A shape touching the edge of the bitmap gets traced along that edge, so the
    mask is padded first and the padding subtracted back out of the
    coordinates. Without it the J and the H fuse into one contour through the
    border.

Why the wordmark is a vector and the mark is not: the wordmark is flat black
type, so it traces exactly and then costs nothing at any size. The mark is a
shaded 3D render — there is no vector of it, and flattening it to a silhouette
turns the ribbon into a blob.
"""
import os
import re
import numpy as np
import potrace
from PIL import Image, ImageDraw, ImageFont

SRC_MARK = "img/Logo.png"
SRC_WORD = "img/Text logo.png"

# The brushed-metal render, on black, delivered separately from the master.
# It is NOT the same camera as SRC_MARK — measured, the silhouettes agree at
# IoU 0.85 and the bounding boxes differ in aspect by 7% — so it can never be
# crossfaded against the master or carry the traced contour. It is only ever
# shown on its own, in the dark, which is the environment it was lit for.
#
# Its lower half carries a JEEV of its own, in chamfered chrome letterforms
# that are not the wordmark's: the E terminals are cut at an angle and the V
# is notched. Two wordmarks would be a brand fault, so build_silver_plate()
# keeps only the mark and the site sets the name in its own drawing.
SRC_SILVER = "img/Silver logo.png"

# The face the division name is set in — the same one TECH is drawn in.
# Measured letter by letter it matches the artwork to within a pixel. The
# filename is not its real name: internally it reports as "Sh Ad Grotesk
# Light", and the repo used to carry a byte-identical second copy of it called
# sui-generis-regular.ttf, which has been removed. Build input only; the site
# ships outlines, never the font.
DIVISION_FONT = "fonts/brandon-grotesque-light.ttf"

GROUND = (247, 247, 245)      # --ground
INK = (26, 29, 31)            # --ink
MUTED = (107, 114, 128)       # --muted
RULE = (212, 214, 216)        # --rule
INK_INVERT = (20, 23, 26)     # --ink-invert, the dark band and the /mark theatre
ON_INVERT = (242, 242, 240)   # --on-invert
MUTED_INVERT = (168, 173, 180)  # --muted-invert
RULE_INVERT = (52, 56, 60)    # --rule-invert


# ---- shared helpers -------------------------------------------------------

def trimmed(path, floor=8):
    """Crop to the ink, not to the halo.

    Both renders carry a ring of alpha=1 around the subject — invisible, but
    getbbox() counts it, and on the mark it added 429 dead pixels down the left
    side. Laid out against a grid that reads as the logo failing to line up."""
    im = Image.open(path).convert("RGBA")
    a = np.array(im.getchannel("A"))
    ys, xs = np.where(a > floor)
    return im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def contours(img, pad=8, turdsize=2):
    w, h = img.size
    mask = np.zeros((h + 2 * pad, w + 2 * pad), dtype=bool)
    mask[pad:pad + h, pad:pad + w] = np.array(img.getchannel("A")) > 127
    path = potrace.Bitmap(~mask).trace(turdsize=turdsize, alphamax=1.0,
                                       opticurve=True, opttolerance=0.2)
    return list(path), pad


def path_d(curves, pad, sx=1.0, sy=1.0, dx=0.0, dy=0.0, precision=2):
    """Curves -> one SVG path string, optionally scaled and translated."""
    fmt = "%%.%df" % precision
    X = lambda v: (fmt % ((v - pad) * sx + dx)).rstrip("0").rstrip(".")
    Y = lambda v: (fmt % ((v - pad) * sy + dy)).rstrip("0").rstrip(".")
    out = []
    for curve in curves:
        s = curve.start_point
        out.append("M%s %s" % (X(s.x), Y(s.y)))
        for seg in curve:
            e = seg.end_point
            if seg.is_corner:
                out.append("L%s %sL%s %s" % (X(seg.c.x), Y(seg.c.y), X(e.x), Y(e.y)))
            else:
                out.append("C%s %s %s %s %s %s" % (X(seg.c1.x), Y(seg.c1.y),
                                                   X(seg.c2.x), Y(seg.c2.y),
                                                   X(e.x), Y(e.y)))
        out.append("Z")
    return "".join(out)


def report(path, note=""):
    print("  %-26s %7s bytes  %s" % (path, "{:,}".format(os.path.getsize(path)), note))


def square(img, size, pad_ratio, bg=None, tint=None):
    """Fit img inside a size x size canvas. bg=None leaves it transparent."""
    canvas = Image.new("RGBA", (size, size), (bg + (255,)) if bg else (0, 0, 0, 0))
    avail = size - 2 * max(1, round(size * pad_ratio))
    w, h = img.size
    sc = min(avail / w, avail / h)
    nw, nh = max(1, round(w * sc)), max(1, round(h * sc))
    r = img.resize((nw, nh), Image.LANCZOS)
    if tint:
        t = Image.new("RGBA", (nw, nh), tint + (255,))
        t.putalpha(r.getchannel("A"))
        r = t
    canvas.paste(r, ((size - nw) // 2, (size - nh) // 2), r)
    return canvas


def inverted(img):
    """Light ribbon on dark: invert the render's luminance, keep its alpha."""
    from PIL import ImageOps
    rgb = ImageOps.invert(img.convert("RGB")).convert("RGBA")
    rgb.putalpha(img.getchannel("A"))
    return rgb


# ---- outputs --------------------------------------------------------------

def build_wordmark(word):
    """img/wordmark.svg — set by CSS mask, so it takes currentColor."""
    curves, pad = contours(word)
    d = path_d(curves, pad)
    w, h = word.size
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
           'role="img" aria-label="JEEV TECH"><title>JEEV TECH</title>'
           '<path fill="currentColor" fill-rule="evenodd" d="%s"/></svg>' % (w, h, d))
    open("img/wordmark.svg", "w", encoding="utf-8").write(svg)
    report("img/wordmark.svg", "%d contours, viewBox %dx%d" % (len(curves), w, h))


def build_division_wordmarks(word):
    """img/wordmark-<division>.svg — JEEV RESEARCH, BIO TECH, ENERGY, ECO, INFRA.

    Only JEEV TECH exists as artwork, but the brand architecture needs the
    same lockup for every division. Rather than set them in a substitute face
    and hope, the geometry is measured off the real thing and reproduced:

      - JEEV is not re-set. Those pixels are lifted straight out of the
        source render, so the master identifier is always the original
        drawing, never an approximation of it. Only the division name is
        typeset.
      - The division face is the one TECH is drawn in. Measured letter by
        letter against the artwork it matches to within a pixel, so setting
        ENERGY beside JEEV is the same operation that produced TECH.
      - Cap height, baseline, the gap after JEEV and the tracking are all
        taken from the artwork rather than chosen. The tracking in particular
        is solved, not eyeballed: it is whatever value reproduces TECH's ink
        width exactly.

    The font is a build input only, like the two source renders. What ships
    is the traced outline — see .vercelignore.

    The order here is the order the divisions are listed on /mark, and it is
    the company's own sequence rather than an alphabet: the mind first
    (TECH, RESEARCH), then the body (BIO TECH), then the world (ENERGY, ECO,
    INFRA). See principles.html#order-of-freedom. A division name may carry a
    space — the tracking loop advances by the space's own width like any other
    glyph — and the filename takes a hyphen where the name takes the space."""
    DIVISIONS = ["TECH", "RESEARCH", "BIO TECH", "ENERGY", "ECO", "INFRA"]

    m = np.array(word.getchannel("A")) > 127
    H, W = m.shape

    # Letter islands. The lockup is tracked, so every letter stands alone.
    cols, runs, start = m.sum(0), [], None
    for i, c in enumerate(cols):
        if c and start is None:
            start = i
        elif not c and start is not None:
            runs.append((start, i)); start = None
    if start is not None:
        runs.append((start, W))
    if len(runs) != 8:
        raise SystemExit("expected 8 letters in the wordmark, found %d" % len(runs))

    def flat_cap(idx):
        """Cap height off flat-topped letters only. A round O or a pointed V
        overshoots the cap line by a couple of percent, and measuring those
        sets every division name a size too large."""
        yy = [np.where(m[:, s:e].any(1))[0] for s, e in idx]
        top = min(int(y.min()) for y in yy)
        base = max(int(y.max()) for y in yy)
        return base - top + 1, base

    jeev_end = runs[3][1]                       # right edge of the V
    _, jeev_base = flat_cap(runs[1:3])          # the two E's
    cap, base = flat_cap([runs[4], runs[5], runs[7]])   # T, E, H — not the C
    gap = runs[4][0] - jeev_end
    tech_ink = runs[7][1] - runs[4][0]

    # Point size that lands the division face on that cap height.
    probe = ImageFont.truetype(DIVISION_FONT, 400)
    im = Image.new("L", (1200, 900), 0)
    ImageDraw.Draw(im).text((100, 200), "H", font=probe, fill=255)
    p = np.array(im) > 127
    ys = np.where(p.any(1))[0]
    size = 400.0 * cap / (ys.max() - ys.min() + 1)
    font = ImageFont.truetype(DIVISION_FONT, int(round(size)))

    def set_word(text, track):
        """Draw text on its own canvas and return (bitmap, ink bounds)."""
        pad = int(size)
        canvas = Image.new("L", (int(size * len(text) * 1.6) + 2 * pad, int(size * 2.4)), 0)
        d = ImageDraw.Draw(canvas)
        x = float(pad)
        for ch in text:
            d.text((x, size * 0.6), ch, font=font, fill=255)
            x += font.getlength(ch) + track
        arr = np.array(canvas) > 127
        xs = np.where(arr.any(0))[0]
        ys = np.where(arr.any(1))[0]
        return arr, int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())

    # Solve the tracking: the value that reproduces TECH's ink width.
    _, x0, x1, _, _ = set_word("TECH", 0.0)
    track = (tech_ink - (x1 - x0 + 1)) / 3.0

    arr, x0, x1, y0, y1 = set_word("TECH", track)
    err = (x1 - x0 + 1) - tech_ink
    print("  wordmark model: cap %d, size %.1f, tracking %.1f (%.4f em), "
          "TECH width err %+dpx" % (cap, size, track, track / size, err))
    if abs(err) > 2:
        raise SystemExit("tracking solve failed (%+dpx)" % err)

    for name in DIVISIONS:
        arr, x0, x1, y0, y1 = set_word(name, track)
        out = np.zeros((H, jeev_end + gap + (x1 - x0 + 1)), bool)
        out[:, :jeev_end] = m[:, :jeev_end]

        # Baseline-align the division name to the artwork's own baseline,
        # then clip anything the taller JEEV block cannot contain.
        top = base - (y1 - y0)
        block = arr[y0:y1 + 1, x0:x1 + 1]
        lo, hi = max(0, top), min(H, top + block.shape[0])
        out[lo:hi, jeev_end + gap:] = block[lo - top:hi - top]

        img = Image.fromarray(np.zeros(out.shape, "uint8")).convert("RGBA")
        img.putalpha(Image.fromarray((out * 255).astype("uint8")))
        curves, pad = contours(img)
        label = "JEEV %s" % name
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
               'role="img" aria-label="%s"><title>%s</title>'
               '<path fill="currentColor" fill-rule="evenodd" d="%s"/></svg>'
               % (out.shape[1], H, label, label, path_d(curves, pad)))
        dest = "img/wordmark-%s.svg" % name.lower().replace(" ", "-")
        open(dest, "w", encoding="utf-8").write(svg)
        note = "%d contours, viewBox %dx%d" % (len(curves), out.shape[1], H)

        # TECH is generated too, as the standing measurement of how good the
        # other four are. It is the one division whose real artwork exists,
        # so re-setting it and comparing tells us exactly what the divisions
        # inherit. Pixels, not bytes: a traced render and a traced re-set
        # differ in the last decimal of every curve, which says nothing about
        # whether the letters are right.
        #
        # It currently lands at 0.84, and that number is the honest state of
        # this: the repo's font is a close relative of the wordmark's face,
        # not the face itself. Cap height, baseline, tracking and overall
        # width are exact — those are measured off the artwork — but the
        # letterforms differ, most visibly on E (about 17% too wide) and H
        # (about 12%). At the sizes these are used it does not read, and the
        # four divisions look like siblings of TECH. With the original font
        # this would rise above 0.97 and the divisions would be exact.
        #
        # So the gate is set just under the current value: it exists to catch
        # drift, not to certify a match that has not happened yet.
        if name == "TECH":
            if out.shape != m.shape:
                raise SystemExit("re-set TECH is %s, artwork is %s" % (out.shape, m.shape))
            iou = (out & m).sum() / float((out | m).sum())
            note += "  — agrees with the real artwork, IoU %.4f" % iou
            if iou < 0.80:
                raise SystemExit("the division model has drifted (IoU %.4f); the "
                                 "other four divisions are no longer trustworthy" % iou)
        report(dest, note)

    # JEEV alone — the master identifier with no division beside it.
    jm = m[:, :jeev_end]
    yy = np.where(jm.any(1))[0]
    jm = jm[yy.min():yy.max() + 1]
    img = Image.fromarray(np.zeros(jm.shape, "uint8")).convert("RGBA")
    img.putalpha(Image.fromarray((jm * 255).astype("uint8")))
    curves, pad = contours(img)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
           'role="img" aria-label="JEEV"><title>JEEV</title>'
           '<path fill="currentColor" fill-rule="evenodd" d="%s"/></svg>'
           % (jm.shape[1], jm.shape[0], path_d(curves, pad)))
    open("img/wordmark-jeev.svg", "w", encoding="utf-8").write(svg)
    report("img/wordmark-jeev.svg", "%d contours, viewBox %dx%d"
           % (len(curves), jm.shape[1], jm.shape[0]))


def build_mark(mark):
    """The mark at chrome size: 44px in the footer, 72px in the sign-off, 36px
       in the header. 360 tall covers all of them at 4x and stays under 25KB.

       The light cut exists because /mark's header crossfades to it as the
       theatre goes dark, and the only light cut that existed was the stage's
       1000px one — 66KB decoded to fill 36 pixels, on every view of the page."""
    px = 360
    for src, dest in ((mark, "img/logo-mark.webp"),
                      (inverted(mark), "img/logo-mark-light.webp")):
        w = round(src.size[0] * px / src.size[1])
        src.resize((w, px), Image.LANCZOS).save(dest, "WEBP", quality=86, method=6)
        report(dest, "%dx%d" % (w, px))


def build_icons(mark):
    """The tab carries the mark, on transparency, with no tile behind it.

    The mark it carries is the *silhouette*, not the render. That is the whole
    trick, and it is what the earlier J was working around: at 16px a shaded
    object is four pixels of grey mush, but the same object as one flat shape
    survives — the loop, the crossing and the hole are all still there. What
    cannot survive 16px is shading, not the mark.

    Transparency costs the one thing a tile gave for free, which is a
    guaranteed contrast. img/icon.svg buys it back by carrying its own
    prefers-color-scheme rule, so the shape is ink on a light tab bar and
    paper on a dark one. Every current browser prefers that file. favicon.ico
    cannot switch — ICO has no such mechanism — so it is cut in ink for the
    light case and left as the fallback it is.

    The home-screen icons keep their ink tile. A transparent icon on an iOS
    home screen composites onto black, and Android will put its own shape
    behind it; both look like a mistake."""
    # The SVG is the one that is actually used. Same contour the /mark page
    # traces, at the same turdsize — specks would trace as their own shapes.
    curves, pad = contours(mark, pad=8, turdsize=500)
    box, inset = 512.0, 0.04
    avail = box * (1 - 2 * inset)
    sc = min(avail / mark.size[0], avail / mark.size[1])
    dx = (box - mark.size[0] * sc) / 2
    dy = (box - mark.size[1] * sc) / 2
    # Two belts before the braces, both for consumers that are not a browser.
    #
    #   width/height as well as viewBox. A browser is happy with a viewBox
    #   alone — it scales the thing to whatever box the tab bar gives it — but
    #   a rasterizer handed an SVG with no intrinsic size has to invent one,
    #   and some decline to.
    #
    #   fill on the path as well as in the <style>. The stylesheet is what
    #   makes this file follow the tab bar, and it stays: a CSS rule beats a
    #   presentation attribute, so the light and dark cases are unchanged in
    #   every browser. But the attribute is what is left if a sanitizer drops
    #   the <style>, and SVG's default fill is black — which on a dark card
    #   is a mark nobody can see. Ink is the better thing to fall back to.
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
           'width="512" height="512" role="img" aria-label="JEEV"><style>'
           'path{fill:%s}'
           '@media(prefers-color-scheme:dark){path{fill:%s}}'
           '</style><path fill="%s" fill-rule="evenodd" d="%s"/></svg>'
           % ("#%02X%02X%02X" % INK, "#%02X%02X%02X" % ON_INVERT,
              "#%02X%02X%02X" % INK,
              path_d(curves, pad, sc, sc, dx, dy, precision=1)))
    open("img/icon.svg", "w", encoding="utf-8").write(svg)
    report("img/icon.svg", "%d contours, mark on transparency, follows the tab bar"
           % len(curves))

    # The raster fallback: the render's own alpha filled flat, so the edge is
    # antialiased rather than traced. Cut once at 128 and let the ICO writer
    # take it down — the small sizes are cleaner from a large master than from
    # a small one.
    square(mark, 128, inset, tint=INK).save(
        "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
    report("favicon.ico", "mark in ink on transparency, 16/32/48")

    inv = inverted(mark)
    for size, dest in ((180, "apple-touch-icon.png"), (192, "img/icon-192.png"),
                       (512, "img/icon-512.png")):
        square(inv, size, 0.10, bg=INK).convert("RGB").save(dest, optimize=True)
        report(dest, "mark on ink, %dx%d" % (size, size))


def build_mark_page(mark):
    """Assets for /mark — the brand-philosophy page.

    The page presents the mark at viewport scale and zooms into its internal
    strands, so it needs far more resolution than the 360px chrome asset.
    2000px wide covers a ~1000px stage at 2x; 1000px serves phones. The
    inverted render feeds the page's dark band, where the divisions are
    listed against the constant mark."""
    # The exhibit crossfades between the two: the object is a dark solid on
    # the light opening, and a lit silver one once the theatre goes dark.
    # Both are needed at stage resolution, so both are cut at both sizes.
    inv = inverted(mark)
    for src, tag in ((mark, ""), (inv, "-light")):
        for px in (2000, 1000):
            h = round(src.size[1] * px / src.size[0])
            dest = "img/mark%s-%d.webp" % (tag, px)
            src.resize((px, h), Image.LANCZOS).save(dest, "WEBP", quality=84, method=6)
            report(dest, "%dx%d%s" % (px, h, ", inverted" if tag else ""))

    # The continuity trace on /mark is this contour: potrace run over the
    # render's own alpha, which is why it is a single closed line with no
    # beginning and no end — the chapter's claim is the geometry's, not a
    # drawing that illustrates it. It has to be inline in the page for the
    # stroke-dash animation (and CSP forbids fetching it), so it is written
    # here for pasting rather than served. turdsize drops the specks that
    # would otherwise trace as their own contours.
    curves, pad = contours(mark, pad=8, turdsize=500)
    sc = 2000.0 / mark.size[0]
    d = path_d(curves, pad, sc, sc, 0, 0, precision=1)
    open("_tools/mark-contour.path.txt", "w").write(d)
    report("_tools/mark-contour.path.txt",
           "%d contours — paste into the trace block of mark.html" % len(curves))

    # /mark used to cut its own favicon, because it was the one page whose
    # tab should show the mark rather than the sitewide J. Every tab shows
    # the mark now, so the exception is gone and the page uses favicon.ico
    # and img/icon.svg like everything else.


def build_silver_plate():
    """img/mark-silver-*.webp — the mark in the dark environment.

    The rest of the page's silver is a luminance inversion of the black
    render: correct in value, but invented in every other way, because a
    negative of a matte surface is not a metal one. This is a real metal
    render, and it goes where the page can afford to show one image large and
    still — the plate below the architecture, at the bottom of the dark act.

    Three things are done to it. The JEEV underneath is cropped away (see the
    note on SRC_SILVER). The black is lifted to --ink-invert, so what remains
    of the render's ground is the colour of the section it sits on. And the
    ground is then cut away entirely: alpha comes from the render's own
    luminance, so the plate is the object and its light, not a rectangle
    containing them.

    That last one is the load-bearing part, and matching the colour is not a
    substitute for it. It was tried: the flat field encodes one or two levels
    off the token — 86-quality WebP will not hold (20, 23, 26) exactly — and
    a step of one level across a field that size still draws a visible
    rectangle. There is no tolerance to hit, so the answer is to have no
    field. What the object's own dark passages lose to transparency they get
    back from the ground behind, which is the same near-black; below about
    L=24 the two are indistinguishable, which is why the cut can be made
    there without eating into the surface."""
    im = Image.open(SRC_SILVER).convert("RGB")
    a = np.array(im).astype(np.float32).mean(axis=2)
    ink = a > 55

    # The mark and the word are separated by a band of empty rows; cut on the
    # widest one rather than a guessed fraction of the height.
    rows = ink.sum(axis=1)
    empty = rows < 4
    runs, start = [], None
    for y in range(len(empty)):
        if empty[y] and start is None:
            start = y
        elif not empty[y] and start is not None:
            runs.append((y - start, start, y))
            start = None
    inner = [r for r in runs if r[1] > 0 and r[2] < len(empty)]
    if not inner:
        raise SystemExit("build_silver_plate: no gap between mark and word")
    _, gap_top, gap_bot = max(inner)
    cut = (gap_top + gap_bot) // 2

    ys, xs = np.nonzero(ink[:cut, :])
    pad = int(round(0.06 * (xs.max() - xs.min() + 1)))   # room for the glow
    box = (max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
           min(im.size[0], int(xs.max()) + 1 + pad),
           min(im.size[1], int(ys.max()) + 1 + pad))
    cropped = np.array(im.crop(box)).astype(np.float32)

    lift = np.array(INK_INVERT, dtype=np.float32)
    lifted = lift + cropped * (255.0 - lift) / 255.0

    def smoothstep(t):
        t = np.clip(t, 0.0, 1.0)
        return t * t * (3 - 2 * t)

    lum = cropped.max(axis=2)
    alpha = smoothstep((lum - 2.0) / 22.0)

    # Inside the object, hold alpha at 1. A cut driven purely by luminance
    # puts every shadow and every gap between the strands into the alpha
    # channel, which more than doubles the file for a difference nobody can
    # see — the ground behind is the same near-black. Filling the object's
    # own extent (opaque between the first and last lit pixel of each row,
    # and of each column) leaves alpha smooth everywhere except the outline,
    # which is the only place it has work to do.
    lit = lum > 24
    span = lambda m, ax: (np.maximum.accumulate(m, axis=ax) &
                          np.flip(np.maximum.accumulate(np.flip(m, ax), axis=ax), ax))
    alpha = np.maximum(alpha, (span(lit, 1) & span(lit, 0)).astype(np.float32))

    # The crop can pass close enough to the object for its glow to reach the
    # edge; a short ramp there keeps the boundary from ever being a line.
    h, w = alpha.shape
    edge = max(4, pad // 2)
    ramp = lambda n: np.clip(np.minimum(np.arange(n), n - 1 - np.arange(n)) /
                             float(edge), 0, 1)
    alpha *= smoothstep(np.minimum(ramp(w)[None, :], ramp(h)[:, None]))

    plate = Image.fromarray(
        np.dstack([lifted.round().clip(0, 255), alpha * 255]).astype("uint8"), "RGBA")

    for px in (2000, 1200):
        ph = round(plate.size[1] * px / plate.size[0])
        dest = "img/mark-silver-%d.webp" % px
        plate.resize((px, ph), Image.LANCZOS).save(dest, "WEBP", quality=86, method=6)
        report(dest, "%dx%d, real metal, edges feathered" % (px, ph))
    return plate


def build_og(mark, word):
    """img/og-image.png — 1200x630. Same layout as before; the wordmark is now
       the real one and the mark signs the corner."""
    W, H, M = 1200, 630, 96
    im = Image.new("RGB", (W, H), GROUND)
    d = ImageDraw.Draw(im)

    wm_h = 26
    wm_w = round(word.size[0] * wm_h / word.size[1])
    wm = word.resize((wm_w, wm_h), Image.LANCZOS)
    tint = Image.new("RGBA", wm.size, INK + (255,))
    tint.putalpha(wm.getchannel("A"))
    im.paste(tint, (M, 78), tint)

    d.line([(M, 158), (W - M, 158)], fill=INK, width=2)

    font = ImageFont.truetype("fonts/newsreader-normal.ttf", 62)
    try:
        font.set_variation_by_axes([400])
    except Exception:
        pass
    for i, line in enumerate(["Engineering human-centric",
                              "technologies that advance civilization."]):
        d.text((M, 196 + i * 82), line, font=font, fill=INK)

    d.line([(M, 404), (M + 584, 404)], fill=INK, width=2)

    mk_h = 132
    mk_w = round(mark.size[0] * mk_h / mark.size[1])
    mk = mark.resize((mk_w, mk_h), Image.LANCZOS)
    im.paste(mk, (W - M - mk_w, H - M - mk_h), mk)

    im.save("img/og-image.png", optimize=True)
    report("img/og-image.png", "%dx%d" % (W, H))


def build_og_mark(plate, word):
    """img/og-mark.png — the share card for /mark.

    The page is the one dark thing on the site, and its subject is the object
    rather than a sentence, so its card is the object lit on the theatre
    ground. Sharing /mark with the site's general card showed a statement the
    page does not make.

    The object here is the real metal render, not the inversion: a share card
    is seen once, small, next to other people's, and the surface is the only
    thing carrying it. The plate arrives on the card's own ground colour with
    a feathered border, so it composites without a seam."""
    W, H, M = 1200, 630, 96
    im = Image.new("RGB", (W, H), INK_INVERT)
    d = ImageDraw.Draw(im)

    mk_h = 470
    mk_w = round(plate.size[0] * mk_h / plate.size[1])
    mk = plate.resize((mk_w, mk_h), Image.LANCZOS)
    im.paste(mk, (W - M - mk_w + 70, (H - mk_h) // 2), mk)

    wm_h = 22
    wm_w = round(word.size[0] * wm_h / word.size[1])
    wm = word.resize((wm_w, wm_h), Image.LANCZOS)
    tint = Image.new("RGBA", wm.size, ON_INVERT + (255,))
    tint.putalpha(wm.getchannel("A"))
    im.paste(tint, (M, M), tint)

    d.line([(M, M + 54), (M + 300, M + 54)], fill=RULE_INVERT, width=1)

    font = ImageFont.truetype("fonts/newsreader-normal.ttf", 58)
    try:
        font.set_variation_by_axes([400])
    except Exception:
        pass
    for i, line in enumerate(["The Mark", "of JEEV"]):
        d.text((M, 250 + i * 74), line, font=font, fill=ON_INVERT)

    small = ImageFont.truetype("fonts/sourceserif4-normal.ttf", 25)
    d.text((M, 430), "Continuity. Emergence. Life.", font=small, fill=MUTED_INVERT)

    im.save("img/og-mark.png", optimize=True)
    report("img/og-mark.png", "%dx%d, the object on the theatre ground" % (W, H))


def main():
    mark, word = trimmed(SRC_MARK), trimmed(SRC_WORD)
    print("sources: mark %s, wordmark %s" % (mark.size, word.size))
    build_wordmark(word)
    build_division_wordmarks(word)
    build_mark(mark)
    build_mark_page(mark)
    build_icons(mark)
    plate = build_silver_plate()
    build_og(mark, word)
    build_og_mark(plate, word)


if __name__ == "__main__":
    main()
