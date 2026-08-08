/* ==========================================================================
   JEEV TECH — Main JavaScript
   Mobile menu toggle. That's all. No tracking, no analytics, no libraries.
   ========================================================================== */

(function () {
  'use strict';

  // Signal that JS is running — the scroll reveal only hides its start
  // state under html.js, so the content is never hidden without it.
  document.documentElement.classList.add('js');

  // Scroll reveal for the one orchestrated moment (Philosophy page).
  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length) {
    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.3 });
      reveals.forEach(function (el) { observer.observe(el); });
    } else {
      reveals.forEach(function (el) { el.classList.add('revealed'); });
    }
  }

  // Sections arrive as they are reached. Classes are added here rather than
  // in the markup so that without JS every section is simply visible.
  var arrivals = document.querySelectorAll('.section, .rail--ruled');
  if (arrivals.length && 'IntersectionObserver' in window) {
    var arriveObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('arrived');
          arriveObserver.unobserve(entry.target);
        }
      });
      // Text and drawings want opposite timing. A diagram should draw once
      // you are looking at it, so its observer shrinks the root. Prose should
      // simply be there when you arrive — so this one grows the root and
      // fires a little before the section enters, which also prevents a blank
      // band during a fast flick-scroll on a phone.
    }, { threshold: 0, rootMargin: '0px 0px 12% 0px' });

    Array.prototype.forEach.call(arrivals, function (el) {
      // Anything already on screen at load stays put — no flash of movement.
      if (el.getBoundingClientRect().top < window.innerHeight * 0.9) return;
      el.classList.add('will-arrive');
      arriveObserver.observe(el);
    });
  }

  // Diagrams draw themselves when reached. Observed separately from
  // sections so that a diagram inside an already-visible section still
  // animates rather than appearing pre-drawn.
  var diagrams = document.querySelectorAll('figure.diagram');

  // Measure every line before anything is observed, so each one is dashed
  // by its own length rather than a shared constant. A shared constant is
  // wrong in both directions: it leaves an undrawn gap on any path longer
  // than it, and it completes a short path — an arrowhead — in the first
  // few percent of the animation, so the head appears before the line that
  // reaches it. Measured lengths also let a whole diagram draw at one
  // constant speed, in document order, like a drafting hand.
  Array.prototype.forEach.call(diagrams, function (fig) {
    var parts = fig.querySelectorAll('.dg-draw');
    if (!parts.length) return;

    var lengths = [];
    var i;
    for (i = 0; i < parts.length; i++) {
      var len = 0;
      if (typeof parts[i].getTotalLength === 'function') {
        try { len = parts[i].getTotalLength(); } catch (e) { len = 0; }
      }
      // A shape we cannot measure keeps the old fixed behaviour rather
      // than collapsing to a zero-length dash and never appearing.
      lengths.push(len > 0 ? len : null);
    }

    // One constant speed per diagram, then compressed to fit a fixed
    // budget so a large drawing does not outstay the reader.
    var SPEED = 1.15;      // ms per user unit
    var BUDGET = 1100;     // ms for the whole drawing
    var raw = 0;
    for (i = 0; i < lengths.length; i++) {
      raw += (lengths[i] === null ? 400 / SPEED : lengths[i]) * SPEED;
    }
    var scale = raw > BUDGET ? BUDGET / raw : 1;

    var elapsed = 0;
    for (i = 0; i < parts.length; i++) {
      var dur = (lengths[i] === null ? 400 : lengths[i] * SPEED) * scale;
      if (lengths[i] !== null) {
        parts[i].style.setProperty('--dg-len', lengths[i]);
      }
      parts[i].style.setProperty('--dg-dur', Math.round(dur) + 'ms');
      parts[i].style.setProperty('--dg-delay', Math.round(elapsed) + 'ms');
      elapsed += dur;
    }

    // Labels start slightly before the last line lands, so the drawing
    // never pauses between its structure and its annotation.
    fig.style.setProperty('--dg-after', Math.max(240, Math.round(elapsed * 0.7)) + 'ms');
  });

  if (diagrams.length && 'IntersectionObserver' in window) {
    // A drawing must not finish before the reader has reached it. A plain
    // threshold fires as soon as a sliver appears at the bottom of the screen,
    // so on a slow scroll the animation is over by the time the diagram is
    // actually in view. Shrinking the root by 25% at the bottom means the
    // figure has to be properly on screen first, and threshold 0 keeps that
    // true for diagrams taller than the viewport, which can never satisfy a
    // large threshold at all.
    var drawObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('arrived');
          drawObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0, rootMargin: '0px 0px -25% 0px' });

    // The sign-off is watched by this observer, not the prose one: it is a
    // thing to watch happen, so it must not have finished before you get
    // there. Same reason as the diagrams.
    var lateArrivals = document.querySelectorAll('figure.diagram, .signature');
    Array.prototype.forEach.call(lateArrivals, function (el) {
      el.classList.add('will-arrive');
      drawObserver.observe(el);
    });
  }

  // A drawing that scrolls sideways has to say so. Measured rather than
  // assumed from a breakpoint: at some widths the diagram fits and a hint
  // would be a lie.
  var frames = document.querySelectorAll('.diagram__frame');
  if (frames.length) {
    var markScrollable = function () {
      Array.prototype.forEach.call(frames, function (el) {
        var scrolls = el.scrollWidth > el.clientWidth + 4;
        el.parentNode.classList.toggle('is-scrollable', scrolls);
      });
    };
    markScrollable();
    window.addEventListener('resize', markScrollable, { passive: true });
    // Fonts land after first paint and change the measurement.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(markScrollable);
    }
  }

  // The header rule appears once the page has moved.
  var header = document.querySelector('.site-header');
  if (header) {
    var scrolled = false;
    var onScroll = function () {
      var past = window.pageYOffset > 8;
      if (past !== scrolled) {
        scrolled = past;
        header.classList.toggle('site-header--scrolled', past);
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Servizo is built but not launched, so the outbound button says so
  // rather than sending anyone to a dead address.
  var servizoBtn = document.getElementById('servizo-external-link');
  var servizoNote = document.getElementById('servizo-soon');
  if (servizoBtn && servizoNote) {
    servizoBtn.addEventListener('click', function () {
      servizoNote.hidden = false;
    });
  }

  var toggle = document.getElementById('menu-toggle');
  var nav = document.getElementById('site-nav');
  var overlay = document.getElementById('nav-overlay');

  if (!toggle || !nav) return;

  function openMenu() {
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-label', 'Close menu');
    nav.setAttribute('data-open', 'true');
    if (overlay) overlay.setAttribute('data-open', 'true');
    // Trap focus: move focus to first nav link
    var firstLink = nav.querySelector('.site-nav__link');
    if (firstLink) firstLink.focus();
  }

  function closeMenu() {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open menu');
    nav.setAttribute('data-open', 'false');
    if (overlay) overlay.setAttribute('data-open', 'false');
    toggle.focus();
  }

  function isOpen() {
    return toggle.getAttribute('aria-expanded') === 'true';
  }

  toggle.addEventListener('click', function () {
    if (isOpen()) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  // Close on overlay click
  if (overlay) {
    overlay.addEventListener('click', closeMenu);
  }

  // Close on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) {
      closeMenu();
    }
  });

  // Close menu on resize to desktop
  var mql = window.matchMedia('(min-width: 769px)');
  mql.addEventListener('change', function (e) {
    if (e.matches && isOpen()) {
      closeMenu();
    }
  });
})();
