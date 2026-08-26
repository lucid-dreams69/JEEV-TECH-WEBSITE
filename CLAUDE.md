# JEEV TECH — website

The public site for JEEV TECH, an engineering company in India. Pre-launch.
Canonical host is the apex, `https://jeevtech.in`, and `www` must 301 to it.
The two must never disagree. They did: Vercel was redirecting www → apex while
every canonical tag, OG url, JSON-LD url and sitemap entry named www, so the
served page pointed at a host that bounced straight back to it. Google had
indexed the www URL, which meant `www.jeevtech.in/favicon.ico` — the icon it
fetches for the search result — was a redirect rather than an image, and the
result showed the placeholder globe. Changing the host means changing all of
it: 10 pages, `sitemap.xml`, `robots.txt`, and the Vercel primary domain.

Plain static HTML / CSS / vanilla JS. **No build step, no framework, no
dependencies.** Eleven pages, all hand-written; CSS is split by concern under
`css/` and loaded in order (tokens → reset → base → layout → components →
diagram → signature → responsive), so later files win on equal specificity.
`/mark` adds `css/mark.css` and `js/mark.js` after those, and nothing else
loads either.

## Running it

```
python _tools/serve.py 8737
```

Do **not** use `python -m http.server`. Every nav link is a clean URL
(`/principles`, `/about`) because `vercel.json` sets `cleanUrls: true`; plain
http.server 404s on all of them and only the home page is reachable.
`_tools/serve.py` mirrors Vercel's `cleanUrls` + `trailingSlash: false`, serves
the real `404.html`, and sends `Cache-Control: no-store` — a stale stylesheet
after an edit is the most common way local testing lies to you.

## Brand assets are generated, not hand-edited

`img/Logo.png` and `img/Text logo.png` are the 7200x5400 sources and are never
served. `python _tools/build-brand-assets.py` turns them into the wordmark SVGs,
the mark WebPs, the whole favicon set and both og-images. Re-run it after
replacing a source; do not edit the outputs.

`img/Silver logo.png` is a third source: the brushed-metal render, delivered
separately, on black. **It is not the same camera as `Logo.png`** — the
silhouettes agree at IoU 0.85 and the bounding boxes differ in aspect by 7% —
so it can never be crossfaded against the master or carry the traced contour.
It is only ever shown alone. Its lower half carries a JEEV of its own in
chamfered chrome letterforms that are *not* the wordmark's, and the build drops
it; the site sets the name from its own drawing. What the build keeps becomes
`img/mark-silver-*.webp`, cut to alpha from the render's own luminance so there
is no rectangle to see, and the /mark share card.

The division lockups — `wordmark-energy.svg` and the rest — are generated the
same way, and **JEEV in them is never re-set**: those pixels are lifted out of
the source render, and only the division word is typeset beside it, at the cap
height, baseline, gap and tracking measured off the real `TECH`. The
`DIVISIONS` list in the build script is **in the order the list appears on
/mark**, which is the company's own sequence — mind (TECH, RESEARCH), body
(BIO TECH), world (ENERGY, ECO, INFRA) — not an alphabet. Renaming or adding
one means: edit `DIVISIONS`, re-run the build, then update `--wm` in
`mark.html` to the new file's viewBox width, because that number is what
drives the lockup's aspect ratio and nothing recomputes it. The build
re-sets `TECH` too and prints how closely it reproduces the artwork. That number
is currently **0.84**, and it is the honest state of the thing: the font in
`fonts/` is a close relative of the wordmark's face, not the face itself (its E
is ~17% too wide, its H ~12%). At the sizes these are used it does not read.
With the original font it would go above 0.97. **If the real font ever turns up,
drop it in and re-run — nothing else needs changing.** Note also that
`brandon-grotesque-light.ttf` is not what it says it is: internally it is *Sh Ad
Grotesk Light*. A byte-identical copy of it called `sui-generis-regular.ttf`,
and a Handel Gothic that was tested and matches nothing, were both removed.

`_tools/RENDER-SPEC.md` is what to hand a 3D artist, and what to re-paste after
a new render arrives.

## /mark

One object on a sticky stage; `js/mark.js` drives a camera, the lighting and
the per-chapter layers from a single scroll position. Things to know:

- **The page is lit in three acts** — the site's ground, then near-black with
  the object's inverted cut, then back. Anything that must survive that reads
  `--x-ink` / `--x-muted` / `--x-rule` / `--x-ground`, which JS writes every
  frame, **not** the page tokens. Use a token there and it will be dark ink on
  a dark ground for a third of the page. This is also why the header carries
  two cuts of the emblem on this page only.
- **Overlay order is load-bearing.** Lighting veils paint *before* the trace
  and strands: lighting acts on the object, annotations are drawn on the glass
  in front of it. Put a veil last and it dims the drawing into invisibility.
- **Stroke widths are in the render's 2000-unit space**, which lands on screen
  at roughly a quarter — and *per chapter*, because the camera's zoom is part
  of that quarter. Continuity is seen at 1.06 and Life at 2.20, so the same
  stroke draws about two and a half times heavier in the strand chapter than
  in the trace chapter. Judge a weight at the zoom its chapter is seen at; the
  strands were given the trace's weights once and became black bars laid
  across the object. What separates a drawing from the surface under it at
  close range is colour and a halo, not mass.
- **The trace and the strand paths are measured, not drawn.** The trace is
  potrace's contour of the render's own alpha — that is why it is a single
  closed line with no beginning and no end, which is the whole claim of the
  Continuity chapter. Both are regenerated from the render; see the render
  spec. Do not nudge them by hand.
- **The camera places a named point of the render at a named point of the
  stage**, so `.exhibit__camera` needs `transform-origin: 0 0` and the object
  must sit at the corner of it. The clip on `.exhibit__viewport` has to land on
  the same x as `.exhibit__rule`, which is on the page grid, not the viewport —
  hence the `max(0px, (100% - page-max) / 2)` term.
- **The object is sized from the zone, never from the viewport.** `--zone-w` is
  the width between the frame's left edge and the rule; `js/mark.js` measures it
  and CSS takes 0.86 of it. Anything above about 0.87 pushes the whole-object
  chapters through the rule and they are cut off, which reads as the mark
  sliding behind the notes. Change a keyframe's `s` or `f` and that ceiling
  moves — the binding one is Continuity. The detail zooms are meant to overrun.
- **Every chapter has a plateau, and the page snaps to it.** `HOLD` in
  `mark.js` compresses each transition into the middle of the segment between
  two chapter centres, so a chapter is fully composed — camera, spotlight,
  lighting, annotations — for 56% of its span rather than for one scroll
  position. Before that, nothing ever reached full: the continuity trace was
  drawn at a weight no reader ever saw. `scroll-snap` then makes the resting
  position the composed one. The snap target is `.exhibit__snap`, a
  zero-height marker at each chapter's centre — **not** the chapter box (taller
  than the viewport, which relaxes snapping to nothing) and **not** the text
  (a quarter viewport off centre on phones). If a keyframe, `HOLD` or the
  marker's position changes, the other two have to be checked: they are three
  statements of the same number. `sc` is measured off
  `documentElement.clientHeight`, which is the snapport, not off the stage,
  which is `100svh`.
- **The house lights come up on `[data-dark-end]`**, the last dark section, and
  its bottom edge is read live rather than cached: it sits below two lazily
  loaded images, so a measured value is stale by the time it matters and the
  header goes light over a dark page. The header also carries `transition: none`
  on this page, because its colour is already written every frame.
- **The close is one lockup, on measurements.** In `.finale` the name is set to
  the width of the mark and the air between them is one cap height of the name
  (`margin-top: 18.8%` — the name's cap height is its width / 5.1906, which is
  the viewBox of `wordmark-jeev.svg`). Both were read off the artwork. Two
  things push the words off that axis and both have to be undone: a `<p>`
  inherits the site's 38em measure, which at 12px is *narrower than the lockup*
  and left-aligned inside it, so it needs `max-width: none`; and tracking is
  added after the last letter too, so a centred tracked line needs
  `padding-left` equal to its own tracking.

## The accent

`--accent` is a deep pine, and it is spent, never sprinkled. In a drawing it
marks the one thing the drawing is about; in the header it marks **Servizo and
nothing else** — every other nav underline is ink. Painting all eight links
green made it a colour the navigation merely *was*, on every page at once,
which is the same as it meaning nothing.

Two consequences worth knowing:

- **It is cut for paper.** On the inverted ground — the dark band, the /mark
  theatre — `--accent` is barely a colour: it reads as a hole. Anything that
  crosses the two lightings needs the light pine instead, which on /mark is
  `--x-accent`, interpolated per frame beside `--x-ink` and the rest.
- **An inline link in band prose takes the accent by default**, and therefore
  disappears. `layout.css` handles `.band p a:not([class])` for exactly this;
  the standalone `.band__link` was already covered, the inline case was not.

## Things that are easy to break

- **The wordmark is a CSS mask, not text.** `.site-footer__wordmark`,
  `.signature__mark`, `.expression__lockup` and `.finale__name` are painted with
  `background-color: currentColor` + `mask: url(...)`, inside an `@supports`
  block at the end of `components.css`. Size them by **height** (the cap height
  of the type beside them), never font-size — height drives width through
  `aspect-ratio`, so any rule that grows their height grows their width off the
  screen.
- **The emblem appears once per page, in the header, and nowhere else.** It
  used to close the footer and the sign-off as well, which put three of them on
  the home page and About. Both were removed on 26 August 2026; the footer and
  the sign-off keep the wordmark, which is a mask and costs nothing. `/mark` is
  the exception at two, and both are in its header — the light and dark cuts it
  crossfades through the three acts.
- **The header carries both: emblem then wordmark, one lockup.** `.site-brand`
  is a flex row on every page. The emblem is a shaded render, so it cannot go
  below about 30px without the loop closing into a smudge, and it cannot take
  the 44px touch minimum either — height drives width. It gets its hit area
  from a `::after` overlay in `responsive.css`.
  - **`align-items: center` is the alignment, and it is only correct because
    JEEV TECH has no descender** — the caps run 1..633 of a 639-unit drawing,
    so the mask's box *is* the cap box. A drawing with a descender would need
    the box shifted; this one does not.
  - **The name is hidden between 769 and 1024px, and nowhere else.** With the
    eight inline links the nav carries today, the space left beside the emblem
    is 137px at 820 and **86px at 769**, against a name 108px wide — so it fits
    at the top of the band and not at the bottom, and a rule that only holds
    for part of a band is no rule. Below 769 the nav goes behind the menu
    button and the name comes back. Notes was pulled from the nav on 26 August
    2026 and restored the same day; with seven links there was 149px at 769 and
    the name would have fitted. Re-measure that band whenever a nav link is
    added or removed — it is the number that decides this.
- **The favicon is the mark's silhouette, and that is not the same asset as
  the header's.** Shading is what dies at 16px, not the mark — one flat shape
  survives where the render is grey mush. `img/icon.svg` is the one browsers
  actually use and it carries its own `prefers-color-scheme` rule, so it is
  ink on a light tab bar and paper on a dark one; `favicon.ico` cannot switch
  and is cut in ink. Do not put a tile behind either — the transparency is the
  point. The home-screen icons (`apple-touch-icon`, `icon-192`, `icon-512`)
  keep their ink tile, because iOS composites transparency onto black.
- **Never write the `transform` property into a rule that can match anything
  inside an SVG — not even `transform: none`.** The SVG `transform`
  *attribute* is the CSS `transform` property, so a CSS rule does not add to
  it, it replaces it, and a rotated label lies back down flat. This shipped:
  the reduced-motion block in `diagram.css` reset `.dg-fade` with
  `transform: none`, and on any machine reporting
  `prefers-reduced-motion: reduce` — which is what Windows' *animation
  effects: off* does to Chrome — "Problem selection" on /principles rendered
  horizontally, straight through the word "Second". Every device with
  animations on was correct, so it read as random. Use the independent
  `translate` / `rotate` / `scale` properties, which compose with the
  attribute instead of replacing it. The same trap bites verification
  harnesses: to reach a diagram's finished state, clear `opacity` and
  `animation` and remove `.will-arrive` — never set a transform.
- **Diagram animation selectors must be `.diagram.arrived`, never a bare
  `.arrived` descendant.** Sections deliberately arrive early so prose is ready
  when you reach it; a descendant selector makes every drawing animate before
  the reader gets there.
- **A dashed line must use `.dg-fade`, never `.dg-draw`.** Both need
  `stroke-dasharray`, so `.dg-draw` silently renders a dashed line solid.
- **Every diagram ships twice**: `.dg-wide` (640 viewBox, desktop) and
  `.dg-narrow` (320 viewBox, phone), swapped at `max-width: 768px`. Scaling one
  drawing to fit a phone was tested and rejected on measurements. Use the
  selector `.diagram svg.dg-narrow` — a bare class loses to `.diagram svg`.
- **A centred `<p>` is not centred on its parent.** `base.css` gives paragraphs
  `max-width: var(--measure)` — 38em, which is a *font-size multiple*, so at
  small type it is narrow. Inside a wide centred block the paragraph sits at
  the left of it, and `text-align: center` then centres the line on the
  paragraph, not on the block. Any centred composition needs `max-width: none`
  on its prose.
- **`/notes` promises only what it holds.** It was taken down on 26 August 2026
  for advertising "engineering decisions, product reasoning, research notes, and
  the things we got wrong" while holding one entry, and restored the same day
  once the audience was settled: for the readers this site is written for, an
  occasional note is the reason to come back and the only sign the company is
  alive. Its lede now claims engineering decisions and product reasoning, which
  is what the two entries are. Do not widen that sentence again without adding
  the entries first.
- **`css/components.css` is the one file in the repo with CRLF line endings.**
  Rewriting it with LF turns a three-line edit into a 1,900-line diff. Check
  before committing.
- **`privacy.html` claims no cookies, no analytics, no third-party requests.**
  Re-verify it against the code before adding any script, embed or hosted asset.
- **Never delete a source image after converting it.**

## Voice

**Display type takes no terminal full stop.** Headings, statements, chapter
titles, the footer tagline and the closing lines all end without one; running
prose, including figure captions, keeps its punctuation. Internal stops inside
a heading stay where they are two beats ("No beginning. No end"). A period at
the end of a heading is the single most reliable tell that copy was not set by
someone who sets copy.

**Caps are for labels, not for sentences.** Eyebrows, rail labels, statuses and
the labels inside a drawing are uppercase and tracked. Figure captions are not:
they run to two hundred characters, and caps strip the ascenders and descenders
a reader uses to recognise a word. They are set in the utility face at
`--text-body-sm`, sentence case, muted.

Every sentence must be identifiable as a Present Fact, an Engineering Principle,
a Research Direction, or a Long-Term Vision — otherwise rewrite or remove it.
No defensive disclaimers, no invented metrics, no marketplace-denial language
about Servizo. Copy in the founder's voice is his to approve; always flag it as
a starting point.

Longer history — settled decisions, rejected approaches and the reasons — lives
in the memory files, not here.
