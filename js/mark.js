/* ==========================================================================
   JEEV TECH — /mark
   The exhibit. One scroll position drives everything: a camera that places a
   named point of the render at a named point of the stage, the lighting that
   takes the room from the site's ground to near-black, and the per-chapter
   layers — the continuity trace, the two spotlights, the strand annotations.

   No libraries, no tracking. One rAF per scroll burst, and every value is a
   pure function of scroll position, so nothing accumulates drift or has to
   be unwound when you scroll back up.
   ========================================================================== */

(function () {
  'use strict';

  var stage = document.querySelector('.exhibit__stage');
  var camera = document.getElementById('exhibit-camera');
  var object = document.getElementById('exhibit-object');
  var rule = document.querySelector('.exhibit__rule');
  var frame = document.querySelector('.exhibit__frame');
  var sheen = document.getElementById('exhibit-sheen');
  var traceSvg = document.getElementById('exhibit-trace');
  var strandsSvg = document.getElementById('exhibit-strands');
  var veilContinuity = document.getElementById('veil-continuity');
  var veilEmergence = document.getElementById('veil-emergence');
  var veilLife = document.getElementById('veil-life');
  /* The house lights come back up as the last dark section clears the header.
     That is no longer the architecture band — the silver plate follows it —
     so the anchor is marked in the markup rather than named here. */
  var band = document.querySelector('[data-dark-end]') ||
             document.querySelector('.band--mark');
  var chapterEls = document.querySelectorAll('[data-chapter]');
  var root = document.body;

  var mqMobile = window.matchMedia('(max-width: 768px)');
  var mqReduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---- Arrivals below the exhibit ----
     Watched like the site's diagrams: these are things to watch happen, so
     they must not have finished before the reader gets there. Runs whether
     or not the exhibit itself is present. */
  var arrivals = document.querySelectorAll('.alone, .finale');
  if (arrivals.length && 'IntersectionObserver' in window) {
    var arriveObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('arrived');
          arriveObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0, rootMargin: '0px 0px -25% 0px' });
    Array.prototype.forEach.call(arrivals, function (el) {
      el.classList.add('will-arrive');
      arriveObserver.observe(el);
    });
  }

  if (!stage || !camera || !object || !chapterEls.length) return;

  /* ---- Camera keyframes, one per chapter, in document order ----
     f: the point of the render under study, in fractions of the image.
     p: where that point is placed, in fractions of the object zone.
     s: zoom.  r: degrees of drift — an object being turned in the hand.

     The image coordinates that matter:
       (0.50, 0.50) the whole object      (0.30, 0.62) the Möbius loop
       (0.72, 0.27) the emerging lobe     (0.71, 0.69) the strand fan     */
  var KEYS = {
    desktop: {
      opening:    { f: [0.50, 0.50], p: [0.52, 0.60], s: 0.94, r: 0 },
      form:       { f: [0.50, 0.50], p: [0.50, 0.50], s: 1.04, r: 0.5 },
      /* Continuity is the one whole-object chapter that used to push past
         the rule: it was zoomed to 1.10 and offset left, which put its right
         edge 4% outside the zone. The trace follows the entire contour, so
         the chapter wants the whole object centred anyway. */
      continuity: { f: [0.50, 0.52], p: [0.50, 0.50], s: 1.06, r: -0.6 },
      emergence:  { f: [0.72, 0.27], p: [0.50, 0.46], s: 1.72, r: 0.8 },
      life:       { f: [0.71, 0.69], p: [0.50, 0.50], s: 2.20, r: -0.4 },
      engineered: { f: [0.50, 0.50], p: [0.50, 0.50], s: 1.02, r: 0 }
    },
    mobile: {
      opening:    { f: [0.50, 0.50], p: [0.50, 0.30], s: 0.96, r: 0 },
      form:       { f: [0.50, 0.50], p: [0.50, 0.28], s: 1.00, r: 0.5 },
      continuity: { f: [0.48, 0.55], p: [0.50, 0.28], s: 1.06, r: -0.6 },
      emergence:  { f: [0.72, 0.27], p: [0.50, 0.27], s: 1.80, r: 0.8 },
      life:       { f: [0.71, 0.69], p: [0.50, 0.28], s: 2.35, r: -0.4 },
      engineered: { f: [0.50, 0.50], p: [0.50, 0.28], s: 1.00, r: 0 }
    }
  };

  /* ---- The two lighting states ---- */
  var LIGHT = { ground: '#F7F7F5', ink: '#1A1D1F', muted: '#6B7280', rule: '#D4D6D8' };
  var DARK  = { ground: '#14171A', ink: '#F2F2F0', muted: '#A8ADB4', rule: '#34383C' };

  var names = [];
  Array.prototype.forEach.call(chapterEls, function (el) {
    names.push(el.getAttribute('data-chapter'));
  });
  var idxOpening = names.indexOf('opening');
  var idxForm = names.indexOf('form');
  var idxContinuity = names.indexOf('continuity');
  var idxEmergence = names.indexOf('emergence');
  var idxLife = names.indexOf('life');

  /* Dash the annotation paths by their own measured lengths, exactly as the
     site's diagrams are — a shared constant would leave the long paths
     unfinished and complete the short ones in the first few percent. */
  function dashable(svg, sel) {
    if (!svg) return [];
    var out = [];
    Array.prototype.forEach.call(svg.querySelectorAll(sel), function (p) {
      var len = 0;
      try { len = p.getTotalLength ? p.getTotalLength() : 0; } catch (e) { len = 0; }
      if (!len) {
        // <use> has no length of its own; measure what it points at.
        var href = p.getAttribute('href') || p.getAttribute('xlink:href');
        var src = href && document.querySelector(href);
        try { len = src && src.getTotalLength ? src.getTotalLength() : 0; } catch (e2) { len = 0; }
      }
      if (len > 0) {
        p.style.strokeDasharray = String(len);
        p.style.strokeDashoffset = String(len);
      }
      out.push({ el: p, len: len });
    });
    return out;
  }
  var tracePaths = dashable(traceSvg, 'use');
  var strandPaths = dashable(strandsSvg, 'path');

  /* ---- Geometry, measured on resize ---- */
  var centers = [];
  var stageW = 0, stageH = 0, objW = 0, objH = 0;
  var zoneL = 0, zoneR = 0;

  function measure() {
    stageW = stage.clientWidth;
    stageH = stage.clientHeight;

    // The object's half of the split. On a phone the split is horizontal,
    // so the zone is the full width and the placement fractions do the work.
    var f = frame ? frame.getBoundingClientRect() : null;
    if (mqMobile.matches || !rule || !f) {
      zoneL = 0;
      zoneR = stageW;
    } else {
      zoneL = f.left;
      zoneR = rule.getBoundingClientRect().left;
    }

    // The object is sized from the zone, so the zone has to be known before
    // it is read back. CSS has an expression for this too, but it is off by
    // the scrollbar; the measured value is the one that matches the rule.
    root.style.setProperty('--zone-w', (zoneR - zoneL).toFixed(1) + 'px');
    objW = object.offsetWidth;
    objH = object.offsetHeight;

    var y = window.pageYOffset;
    centers = [];
    Array.prototype.forEach.call(chapterEls, function (el) {
      var r = el.getBoundingClientRect();
      centers.push(y + r.top + r.height / 2);
    });
  }

  function ease(t) { return t * t * (3 - 2 * t); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

  function mixHex(a, b, t) {
    var r = Math.round(lerp(parseInt(a.substr(1, 2), 16), parseInt(b.substr(1, 2), 16), t));
    var g = Math.round(lerp(parseInt(a.substr(3, 2), 16), parseInt(b.substr(3, 2), 16), t));
    var l = Math.round(lerp(parseInt(a.substr(5, 2), 16), parseInt(b.substr(5, 2), 16), t));
    return 'rgb(' + r + ',' + g + ',' + l + ')';
  }

  function setDraw(paths, progress, stagger) {
    for (var i = 0; i < paths.length; i++) {
      if (!paths[i].len) continue;
      var local = stagger
        ? clamp01(progress * (1 + stagger * paths.length) - stagger * i)
        : progress;
      paths[i].el.style.strokeDashoffset = String(paths[i].len * (1 - local));
    }
  }

  function update() {
    var keys = KEYS[mqMobile.matches ? 'mobile' : 'desktop'];
    var y = window.pageYOffset;
    var sc = y + stageH * 0.5;

    /* Read before anything is written, so the frame costs one layout and not
       two. This one is read every frame rather than cached with the rest of
       the geometry: the dark act ends below two lazily-loaded images, so its
       bottom edge moves after the measurement pass has run — and a stale
       value here is a light header over a dark page, which is the one thing
       the lighting exists to prevent. */
    var darkBottom = band ? band.getBoundingClientRect().bottom : -Infinity;

    /* Active segment between adjacent chapter centres. */
    var k = 0;
    while (k < centers.length - 2 && sc > centers[k + 1]) k++;
    var span = centers[k + 1] - centers[k] || 1;
    var e = ease(clamp01((sc - centers[k]) / span));

    /* Chapter activations: 1 at a chapter's own centre, 0 at its neighbours'. */
    var a = [];
    for (var i = 0; i < centers.length; i++) a.push(0);
    a[k] = 1 - e;
    a[k + 1] = e;
    if (sc <= centers[0]) { a[0] = 1; a[1] = 0; }
    if (sc >= centers[centers.length - 1]) {
      a[centers.length - 1] = 1;
      a[centers.length - 2] = 0;
    }

    /* Lighting. Down between the opening and the first chapter; back up as
       the dark band's bottom edge reaches the header, so the fixed header is
       never light-on-dark or dark-on-light for even a frame. */
    var down = clamp01((sc - centers[idxOpening]) /
      ((centers[idxForm] - centers[idxOpening]) || 1));
    var up = band ? clamp01((darkBottom - 90) / 260) : 1;
    var t = Math.min(ease(down), up);

    root.style.setProperty('--x-t', t.toFixed(3));
    root.style.setProperty('--x-ground', mixHex(LIGHT.ground, DARK.ground, t));
    root.style.setProperty('--x-ink', mixHex(LIGHT.ink, DARK.ink, t));
    root.style.setProperty('--x-muted', mixHex(LIGHT.muted, DARK.muted, t));
    root.style.setProperty('--x-rule', mixHex(LIGHT.rule, DARK.rule, t));

    /* Draw progress for a traced layer: complete by its chapter's centre,
       held once past it. */
    function approach(idx) {
      if (idx < 1) return 1;
      if (sc >= centers[idx]) return 1;
      if (sc <= centers[idx - 1]) return 0;
      return ease((sc - centers[idx - 1]) / ((centers[idx] - centers[idx - 1]) || 1));
    }

    if (!mqReduce.matches) {
      var ka = keys[names[k]], kb = keys[names[k + 1]] || ka;
      var s = lerp(ka.s, kb.s, e);
      var r = lerp(ka.r, kb.r, e);
      var fx = lerp(ka.f[0], kb.f[0], e), fy = lerp(ka.f[1], kb.f[1], e);
      var px = lerp(ka.p[0], kb.p[0], e), py = lerp(ka.p[1], kb.p[1], e);

      // Place the focal point of the render at the named point of the zone.
      var tx = zoneL + px * (zoneR - zoneL) - s * fx * objW;
      var ty = py * stageH - s * fy * objH;

      camera.style.transform = 'translate3d(' + tx.toFixed(1) + 'px,' +
        ty.toFixed(1) + 'px,0) scale(' + s.toFixed(4) + ')';
      // The drift turns the object about its own centre, which is what
      // turning it in the hand does; on the camera it would swing the frame.
      object.style.transform = 'rotate(' + r.toFixed(2) + 'deg)';

      if (traceSvg) setDraw(tracePaths, approach(idxContinuity), 0);
      if (strandsSvg) setDraw(strandPaths, approach(idxLife), 0.18);
      if (veilContinuity) veilContinuity.style.opacity = a[idxContinuity].toFixed(3);
      if (veilEmergence) veilEmergence.style.opacity = a[idxEmergence].toFixed(3);
      if (veilLife) veilLife.style.opacity = a[idxLife].toFixed(3);
      if (sheen) sheen.style.opacity = (a[idxOpening] * 0.9).toFixed(3);
    } else {
      /* Reduced motion: the object is composed once and stays there. The
         lighting still changes — that is a change of state, not movement —
         but nothing scrubs, and the spotlights are dropped rather than
         dimming a region the static camera is not looking at. */
      var kf = keys.form;
      var ss = kf.s;
      camera.style.transform = 'translate3d(' +
        (zoneL + kf.p[0] * (zoneR - zoneL) - ss * kf.f[0] * objW).toFixed(1) + 'px,' +
        (kf.p[1] * stageH - ss * kf.f[1] * objH).toFixed(1) + 'px,0) scale(' +
        ss.toFixed(4) + ')';
      object.style.transform = 'none';
      if (traceSvg) setDraw(tracePaths, 1, 0);
      if (strandsSvg) setDraw(strandPaths, 1, 0);
      if (veilContinuity) veilContinuity.style.opacity = '0';
      if (veilEmergence) veilEmergence.style.opacity = '0';
      if (veilLife) veilLife.style.opacity = '0';
      if (sheen) sheen.style.opacity = '0';
    }

    if (traceSvg) traceSvg.style.opacity = (a[idxContinuity] * 0.92).toFixed(3);
    if (strandsSvg) strandsSvg.style.opacity = a[idxLife].toFixed(3);
  }

  /* ---- Scheduling ---- */
  var ticking = false;
  function requestTick() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      ticking = false;
      update();
    });
  }

  function remeasure() {
    measure();
    requestTick();
  }

  window.addEventListener('scroll', requestTick, { passive: true });
  window.addEventListener('resize', remeasure, { passive: true });
  window.addEventListener('load', remeasure);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(remeasure);
  }

  remeasure();
})();
