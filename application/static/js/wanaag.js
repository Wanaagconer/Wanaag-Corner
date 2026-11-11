/* ═══════════════════════════════════════════════════════════════
   WANAAG CORNER — moteur d'interactions
   Aucune dépendance obligatoire. Utilise Lenis / GSAP s'ils sont chargés.
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  var REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FINE = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var body = document.body;
  var IS_PUBLIC = body.classList.contains('is-public');
  window.WC = window.WC || {};

  /* ── Sidebar (fonction globale utilisée par les templates) ── */
  window.toggleSidebar = function () {
    var s = document.getElementById('sidebar'), o = document.getElementById('sidebarOverlay');
    if (s) s.classList.toggle('open');
    if (o) o.classList.toggle('open');
  };

  /* ── Défilement fluide (pages publiques) ── */
  var lenis = null;
  if (IS_PUBLIC && !REDUCED && window.Lenis) {
    lenis = new window.Lenis({ duration: 1.15, easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); }, smoothWheel: true });
    WC.lenis = lenis;
    if (window.gsap && window.ScrollTrigger) {
      lenis.on('scroll', window.ScrollTrigger.update);
      window.gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
      window.gsap.ticker.lagSmoothing(0);
    } else {
      (function raf(t) { lenis.raf(t); requestAnimationFrame(raf); })(0);
    }
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var id = a.getAttribute('href');
        if (id.length < 2) return;
        var t = document.querySelector(id);
        if (!t) return;
        e.preventDefault();
        lenis.scrollTo(t, { offset: -40 });
      });
    });
  }

  /* ── Préchargeur (première visite de la session) ── */
  var loader = document.getElementById('wcLoader');
  function startPage() {
    body.classList.add('is-ready');
    document.dispatchEvent(new CustomEvent('wc:ready'));
  }
  if (loader) {
    var seen = false;
    try { seen = sessionStorage.getItem('wc_loaded'); } catch (e) {}
    if (seen || REDUCED) {
      loader.classList.add('is-hidden');
      requestAnimationFrame(startPage);
    } else {
      try { sessionStorage.setItem('wc_loaded', '1'); } catch (e) {}
      var go = function () {
        setTimeout(function () {
          loader.classList.add('is-done');
          setTimeout(startPage, 380);
          setTimeout(function () { loader.classList.add('is-hidden'); }, 1200);
        }, 1500);
      };
      if (document.readyState === 'complete') go(); else window.addEventListener('load', go);
    }
  } else {
    requestAnimationFrame(startPage);
  }

  /* ── Rideau de transition entre les pages ── */
  var curtain = document.getElementById('wcCurtain');
  if (curtain && !REDUCED) {
    // Sortie du rideau à l'arrivée sur la page
    if (sessionStorage.getItem('wc_curtain')) {
      sessionStorage.removeItem('wc_curtain');
      curtain.classList.add('is-in');
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        curtain.classList.add('is-leaving');
        setTimeout(function () { curtain.classList.remove('is-in', 'is-leaving'); }, 800);
      }); });
    }
    document.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest('a');
      if (!a || !a.href) return;
      if (a.target && a.target !== '_self') return;
      if (a.hasAttribute('download') || a.dataset.noTransition !== undefined) return;
      var url;
      try { url = new URL(a.href, location.href); } catch (err) { return; }
      if (url.origin !== location.origin) return;
      if (/^(mailto|tel|javascript):/i.test(a.getAttribute('href') || '')) return;
      if (url.pathname === location.pathname && url.hash) return;
      if ((a.getAttribute('href') || '').charAt(0) === '#') return;
      if (/\/(admin|media)\//.test(url.pathname) && !/admin-panel/.test(url.pathname)) return;
      e.preventDefault();
      try { sessionStorage.setItem('wc_curtain', '1'); } catch (err) {}
      curtain.classList.remove('is-leaving');
      curtain.classList.add('is-in');
      setTimeout(function () { location.href = url.href; }, 620);
    });
    window.addEventListener('pageshow', function (ev) {
      if (ev.persisted) curtain.classList.remove('is-in', 'is-leaving');
    });
  }

  /* ── Curseur ── */
  if (FINE && !REDUCED) {
    var ring = document.createElement('div'); ring.className = 'wc-cursor';
    ring.innerHTML = '<span class="wc-cursor-label"></span>';
    var dot = document.createElement('div'); dot.className = 'wc-cursor-dot';
    body.appendChild(ring); body.appendChild(dot);
    var label = ring.firstChild;
    var mx = -100, my = -100, rx = -100, ry = -100;
    document.addEventListener('mousemove', function (e) {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = 'translate(' + mx + 'px,' + my + 'px)';
      if (!ring.classList.contains('is-visible')) { ring.classList.add('is-visible'); dot.classList.add('is-visible'); rx = mx; ry = my; }
    }, { passive: true });
    document.addEventListener('mouseleave', function () { ring.classList.remove('is-visible'); dot.classList.remove('is-visible'); });
    (function loop() {
      rx += (mx - rx) * 0.16; ry += (my - ry) * 0.16;
      ring.style.transform = 'translate(' + rx + 'px,' + ry + 'px)';
      requestAnimationFrame(loop);
    })();
    document.addEventListener('mouseover', function (e) {
      var t = e.target;
      var lab = t.closest('[data-cursor]');
      var interactive = t.closest('a, button, [role="button"], label[for], .wgt-chip, select, summary');
      var text = t.closest('input[type=text], input[type=email], input[type=password], input[type=search], textarea, [contenteditable="true"]');
      ring.classList.toggle('has-label', !!lab);
      label.textContent = lab ? lab.getAttribute('data-cursor') : '';
      ring.classList.toggle('is-hover', !!interactive && !lab);
      ring.classList.toggle('is-text', !!text && !lab);
      ring.classList.toggle('on-dark', !!t.closest('[data-dark], .sidebar, .public-footer, .wgt-head'));
      dot.style.opacity = (interactive || text || lab) ? '0' : '';
    });
  }

  /* ── Boutons magnétiques ── */
  if (FINE && !REDUCED) {
    document.querySelectorAll('[data-magnetic], .wc-btn, .nav-cta, .wgt-bubble').forEach(function (el) {
      var strength = parseFloat(el.getAttribute('data-magnetic')) || 0.32;
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        var x = e.clientX - r.left - r.width / 2, y = e.clientY - r.top - r.height / 2;
        el.style.transform = 'translate(' + x * strength + 'px,' + y * strength + 'px)';
      });
      el.addEventListener('mouseleave', function () { el.style.transform = ''; });
    });
  }

  /* ── Ondulation au clic ── */
  document.addEventListener('pointerdown', function (e) {
    var b = e.target.closest('.btn, .wc-btn, .nav-item, .wgt-send');
    if (!b || REDUCED) return;
    var r = b.getBoundingClientRect(), s = Math.max(r.width, r.height);
    var span = document.createElement('span');
    span.className = 'wc-ripple';
    span.style.cssText = 'width:' + s + 'px;height:' + s + 'px;left:' + (e.clientX - r.left - s / 2) + 'px;top:' + (e.clientY - r.top - s / 2) + 'px';
    if (getComputedStyle(b).position === 'static') b.style.position = 'relative';
    b.style.overflow = 'hidden';
    b.appendChild(span);
    setTimeout(function () { span.remove(); }, 750);
  });

  /* ── Barre de progression, navigation, topbar ── */
  var prog = document.querySelector('.wc-progress i');
  var nav = document.querySelector('.public-nav');
  var topbar = document.querySelector('.app-topbar');
  var lastY = 0, ticking = false;
  var darkSections = [];
  function collectDark() { darkSections = Array.prototype.slice.call(document.querySelectorAll('[data-dark]')); }
  collectDark();
  function onScroll() {
    var y = window.scrollY || window.pageYOffset;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    if (prog) prog.style.transform = 'scaleX(' + (h > 0 ? y / h : 0) + ')';
    if (nav) {
      nav.classList.toggle('is-scrolled', y > 30);
      if (!body.classList.contains('menu-open')) nav.classList.toggle('is-hidden', y > lastY && y > 320);
      var probe = 40, dark = false;
      for (var i = 0; i < darkSections.length; i++) {
        var r = darkSections[i].getBoundingClientRect();
        if (r.top <= probe && r.bottom >= probe) { dark = true; break; }
      }
      nav.classList.toggle('on-dark', dark);
    }
    if (topbar) topbar.classList.toggle('is-scrolled', y > 8);
    lastY = y; ticking = false;
  }
  window.addEventListener('scroll', function () { if (!ticking) { requestAnimationFrame(onScroll); ticking = true; } }, { passive: true });
  window.addEventListener('resize', collectDark);
  onScroll();

  /* ── Menu mobile ── */
  WC.toggleMenu = function () {
    body.classList.toggle('menu-open');
    if (lenis) { body.classList.contains('menu-open') ? lenis.stop() : lenis.start(); }
  };
  document.querySelectorAll('.wc-menu a').forEach(function (a) {
    a.addEventListener('click', function () { body.classList.remove('menu-open'); if (lenis) lenis.start(); });
  });

  /* ── Découpage du texte en mots (titres animés) ── */
  function splitText(el) {
    if (el.dataset.splitDone) return;
    el.dataset.splitDone = '1';
    var html = el.innerHTML.split(/<br\s*\/?>/i);
    var i = 0;
    el.innerHTML = html.map(function (line) {
      var tmp = document.createElement('div'); tmp.innerHTML = line;
      var out = '';
      tmp.childNodes.forEach(function (node) {
        if (node.nodeType === 3) {
          node.textContent.split(/(\s+)/).forEach(function (w) {
            if (!w) return;
            if (/^\s+$/.test(w)) { out += ' '; return; }
            out += '<span class="split-word" style="--i:' + (i++) + '">' + w + '</span>';
          });
        } else {
          out += '<span class="split-word" style="--i:' + (i++) + '">' + node.outerHTML + '</span>';
        }
      });
      return '<span class="split-line">' + out + '</span>';
    }).join('');
  }
  document.querySelectorAll('[data-split]').forEach(splitText);

  /* ── Révélations au défilement ── */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      en.target.classList.add('is-in', 'animated');
      io.unobserve(en.target);
    });
  }, { threshold: 0.14, rootMargin: '0px 0px -8% 0px' });
  function observeReveals(root) {
    (root || document).querySelectorAll('[data-reveal], [data-split]:not([data-split="manual"]), .ft-giant').forEach(function (el) {
      if (el.closest('[data-hero]')) return; // les héros sont animés après le préchargeur
      io.observe(el);
    });
    // clip-path masque la cible pour IntersectionObserver : on observe le parent
    (root || document).querySelectorAll('[data-clip]').forEach(function (el) {
      if (el.closest('[data-hero]')) return;
      var host = el.parentElement;
      var cio = new IntersectionObserver(function (en) {
        if (en[0].isIntersecting) { el.classList.add('is-in'); cio.disconnect(); }
      }, { threshold: 0.1 });
      cio.observe(host);
    });
  }
  observeReveals();
  document.addEventListener('wc:ready', function () {
    document.querySelectorAll('[data-hero] [data-reveal], [data-hero] [data-clip], [data-hero] [data-split]').forEach(function (el) {
      el.classList.add('is-in');
    });
  });

  /* Révélation automatique des pages internes (non réécrites) */
  if (!REDUCED) {
    var auto = [];
    document.querySelectorAll('.app-content > *, .public-page-content > *').forEach(function (el) {
      if (el.matches('script, style, [data-no-auto], [data-hero], .django-messages') || el.querySelector('[data-reveal], [data-split], [data-clip]')) return;
      auto.push(el);
    });
    ['.psy-grid > *', '.dash-grid > *', '.adm-stats-grid > *', '.forum-groups-grid > *', '.ressources-grid > *',
     '.consultations-list > *', '.requests-list > *', '.posts-grid > *', '.modules-grid > *', '.annonces-row > *'].forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el, i) {
        if (el.closest('[data-no-auto]') || el.hasAttribute('data-reveal')) return;
        auto.push(el); if (i > 0 && i < 6) el.classList.add('d' + i);
      });
    });
    auto.forEach(function (el) { el.classList.add('wow'); io.observe(el); });
  }
  // éléments marqués .wow directement dans les templates
  document.querySelectorAll('.wow').forEach(function (el) { if (REDUCED) el.classList.add('animated'); else io.observe(el); });

  /* Filet de sécurité : tout ce qui est déjà passé à l'écran est révélé */
  var sweepT = null;
  function sweep() {
    var vh = window.innerHeight;
    document.querySelectorAll('.wow:not(.animated), [data-reveal]:not(.is-in), [data-split]:not(.is-in)').forEach(function (el) {
      if (el.closest('[data-hero]') && !body.classList.contains('is-ready')) return;
      if (el.getBoundingClientRect().top < vh * 0.95) el.classList.add('is-in', 'animated');
    });
  }
  window.addEventListener('scroll', function () { clearTimeout(sweepT); sweepT = setTimeout(sweep, 140); }, { passive: true });
  window.addEventListener('load', function () { setTimeout(sweep, 600); });

  /* ── Compteurs ── */
  var countIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      var el = en.target, end = parseFloat(el.getAttribute('data-count')) || 0, dur = 1600, t0 = null;
      countIO.unobserve(el);
      (function step(ts) {
        if (!t0) t0 = ts;
        var p = Math.min(1, (ts - t0) / dur), e = 1 - Math.pow(1 - p, 4);
        el.textContent = Math.round(end * e).toLocaleString('fr-FR');
        if (p < 1) requestAnimationFrame(step);
      })(performance.now());
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('[data-count]').forEach(function (el) { countIO.observe(el); });

  /* ── Inclinaison 3D ── */
  if (FINE && !REDUCED) {
    document.querySelectorAll('[data-tilt]').forEach(function (el) {
      var max = parseFloat(el.getAttribute('data-tilt')) || 6;
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = 'perspective(900px) rotateY(' + px * max + 'deg) rotateX(' + (-py * max) + 'deg)';
        el.style.setProperty('--mx', (px + 0.5) * 100 + '%');
        el.style.setProperty('--my', (py + 0.5) * 100 + '%');
      });
      el.addEventListener('mouseleave', function () { el.style.transform = ''; });
    });
  }

  /* ── Parallaxe légère (sans GSAP) ── */
  var pEls = Array.prototype.slice.call(document.querySelectorAll('[data-parallax]'));
  if (pEls.length && !REDUCED) {
    var pTick = false;
    var pUpdate = function () {
      var vh = window.innerHeight;
      pEls.forEach(function (el) {
        var r = el.parentElement.getBoundingClientRect();
        if (r.bottom < 0 || r.top > vh) return;
        var sp = parseFloat(el.getAttribute('data-parallax')) || 0.12;
        var c = (r.top + r.height / 2 - vh / 2);
        el.style.transform = 'translate3d(0,' + (-c * sp) + 'px,0) scale(1.12)';
      });
      pTick = false;
    };
    window.addEventListener('scroll', function () { if (!pTick) { requestAnimationFrame(pUpdate); pTick = true; } }, { passive: true });
    pUpdate();
  }

  /* ── Pied de page : mot géant ── */
  document.querySelectorAll('.ft-giant span').forEach(function (s, i) { s.style.transitionDelay = (i * 0.06) + 's'; });

  /* ── Indicateur de chargement sur les formulaires ── */
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('button[type="submit"]');
      if (!btn || btn.classList.contains('is-loading')) return;
      setTimeout(function () {
        btn.classList.add('is-loading');
        setTimeout(function () { btn.classList.remove('is-loading'); }, 4000);
      }, 0);
    });
  });

  /* ── Salutation selon l'heure ── */
  document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-greet]').forEach(function (el) {
    var h = new Date().getHours();
    el.textContent = h < 5 ? 'Bonne nuit' : h < 12 ? 'Bonjour' : h < 18 ? 'Bon après-midi' : 'Bonsoir';
  });
  document.querySelectorAll('[data-today]').forEach(function (el) {
    var s = new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    el.textContent = s.charAt(0).toUpperCase() + s.slice(1);
  });
  });

  /* ── Respiration guidée (accessible partout) ── */
  var breath = document.getElementById('wcBreath');
  if (breath) {
    var orb = breath.querySelector('.wc-breath-orb');
    var word = breath.querySelector('.wc-breath-word');
    var cap = breath.querySelector('.wc-breath-cap');
    var timers = [];
    var PHASES = [
      { t: 'Inspirez', s: 'par le nez', d: 4000, scale: 1.1 },
      { t: 'Retenez', s: 'doucement', d: 4000, scale: 1.1 },
      { t: 'Expirez', s: 'par la bouche, lentement', d: 6000, scale: 0.7 }
    ];
    var clearT = function () { timers.forEach(clearTimeout); timers = []; };
    var cycle = function (n) {
      if (n >= 5) { word.innerHTML = 'Merci<small>Revenez ici quand vous voulez.</small>'; orb.style.transitionDuration = '3s'; orb.style.transform = 'scale(.85)'; return; }
      cap.textContent = 'Cycle ' + (n + 1) + ' sur 5';
      var acc = 0;
      PHASES.forEach(function (p) {
        timers.push(setTimeout(function () {
          word.innerHTML = p.t + '<small>' + p.s + '</small>';
          orb.style.transitionDuration = p.d + 'ms';
          orb.style.transform = 'scale(' + p.scale + ')';
        }, acc));
        acc += p.d;
      });
      timers.push(setTimeout(function () { cycle(n + 1); }, acc));
    };
    WC.breathe = function () {
      clearT();
      breath.classList.add('is-open');
      if (lenis) lenis.stop();
      word.innerHTML = 'Installez-vous<small>On commence dans un instant</small>';
      orb.style.transitionDuration = '2s'; orb.style.transform = 'scale(.7)';
      cap.textContent = 'Cinq cycles, à peu près une minute.';
      timers.push(setTimeout(function () { cycle(0); }, 2600));
    };
    WC.breatheStop = function () {
      clearT(); breath.classList.remove('is-open'); if (lenis) lenis.start();
    };
    breath.querySelector('.wc-breath-close').addEventListener('click', WC.breatheStop);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && breath.classList.contains('is-open')) WC.breatheStop(); });
    document.querySelectorAll('[data-breathe]').forEach(function (b) { b.addEventListener('click', function (e) { e.preventDefault(); WC.breathe(); }); });
  }
})();
