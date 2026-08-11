# Render spec — the mark, for /mark

What to export from the 3D file, and where to put it. Everything the site
serves is generated from these by `_tools/build-brand-assets.py`; nothing here
is edited by hand afterwards.

## Why this is needed

`img/Logo.png` is 7200×5400, but the mark inside it occupies only **2824×2005**
real pixels — the rest is empty margin. The Life chapter of /mark magnifies the
object about 2.2×, which on a retina screen asks for roughly **4,400 pixels**
across. That is where the softness comes from, and no amount of processing
invents detail that is not in those 2824 pixels.

Two renders fix it: one larger master, and one close-up per chapter that pushes
in. A detail plate is a *separate render at full resolution*, not a crop — that
is the whole point.

## The exports

All of them:

- **PNG, RGBA, transparent background.** No backdrop, no ground plane, no
  shadow catcher. The page composites the object onto its own ground and
  inverts it for the dark act; a baked background breaks both.
- **Same material, same lighting, same camera rig** as the existing render.
  The page crossfades between full views and close-ups, and a relit object
  reads as a different object.
- **No motion blur, no depth of field, no bloom.** The page does its own
  lighting; a blurred region cannot be sharpened back.
- **16-bit is fine, sRGB.** Denoise on. Samples high enough that the flat
  surfaces are clean — noise is what survives magnification most visibly.

| # | File | Framing | Size (long edge) |
|---|------|---------|------------------|
| 1 | `img/Logo.png` (replace) | The whole mark, as it is framed today | **6000 px** |
| 2 | `img/mark-detail-emergence.png` | Tight on the upper-right lobe where the surface climbs out of the loop | **4000 px** |
| 3 | `img/mark-detail-strands.png` | Tight on the lower-right fan and its internal strands | **4000 px** |
| 4 | `img/Silver logo.png` (replace) | The whole mark in brushed metal, mark only — no wordmark under it | **4000 px** |

Number 4 is the optional one, and it comes with a condition. The metal render
already in the repo is a *different camera* from `Logo.png`: measured, the
silhouettes agree at IoU 0.85 and the bounding boxes differ in aspect by 7%.
That is why the page shows it alone, on its own plate, and never against the
black one. If it can be re-rendered from the master camera, say so — the two
could then be shown together, and the whole light/dark duality of the identity
becomes something the page can demonstrate side by side instead of across a
page turn. If it cannot, leave it as it is; nothing is broken.

For 2 and 3: frame so the region of interest fills about 70% of the frame, and
keep the **same camera angle** as the master — this is a longer lens on the same
object, not a new viewpoint. Leave the object's own edges visible where they
fall; the page decides what to crop.

### If a turntable is easy to produce as well

Optional, and only worth it if the rig already supports it: 48 frames of one
full rotation about the vertical axis, 1600 px wide, same lighting, named
`img/turn/turn-00.png` … `turn-47.png`. That would let the object genuinely
rotate under the scroll instead of the camera panning a still. Say so before
rendering it — the page needs a different loading strategy for a sequence, and
it is not worth the bytes unless the whole set is there.

## After the files land

```
python _tools/build-brand-assets.py
python _tools/trace-strands.py
```

The first regenerates every served asset — the wordmarks, the mark at stage
sizes, the inverted cut, the silver plate, the icons, both og images. The
second re-measures the strand annotations against the new render.

Three things then need pasting or checking, because they are measured in the
render's own coordinates and a re-frame moves all of them:

1. **The continuity trace.** The build writes it to
   `_tools/mark-contour.path.txt`. Paste it into the `<defs>` of the trace
   block in `mark.html`. It has to be inline for the drawing animation, and
   the site's own security policy forbids fetching it at runtime.
2. **The strand annotations.** `trace-strands.py` prints one path per groove
   and writes a numbered proof sheet to `_tools/strand-proof.png`. Not every
   groove is a strand — the ribbon's outer edge and inner fold are grooves
   too — so look at the sheet, take the ones that are strands, paste those
   into the strands block of `mark.html`.
3. **The camera focal points**, in `js/mark.js` — the `f:` pairs in `KEYS`.
   They are fractions of the image: in the current framing the emerging lobe
   is at (0.72, 0.27) and the strand fan at (0.71, 0.69).

If the master is re-framed rather than just re-rendered larger, expect to
adjust 3 by eye; 1 and 2 are mechanical.
