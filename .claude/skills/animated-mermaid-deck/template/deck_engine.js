/* Animated Mermaid Deck — engine
 *
 * Reads window.DECK (injected by the builder), builds the scene DOM, pre-renders
 * each scene's Mermaid to SVG, then drives a timeline that reveals text beats and
 * diagram elements in lockstep, with optional Web Speech narration.
 *
 * Edge reveal tokens are pre-resolved to "edge:N" by the Python builder, so this
 * file only deals with: node ids, subgraph/cluster ids, and "edge:N".
 */
(function () {
  "use strict";

  var DECK = window.DECK || { scenes: [] };
  var SCENES = DECK.scenes || [];
  var BEAT_STAGGER = 700;          // ms between auto-staggered beats
  var REVEAL_STAGGER = 130;        // ms between elements within one build step
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SPEECH_OK = "speechSynthesis" in window;

  // Voices load asynchronously in Chrome/Edge; cache them and refresh on the
  // voiceschanged event so speak() always sees the latest list.
  var VOICES = [];
  var started = false;   // becomes true after the first Play
  function loadVoices() { if (SPEECH_OK) VOICES = window.speechSynthesis.getVoices() || []; }
  if (SPEECH_OK) {
    loadVoices();
    try {
      window.speechSynthesis.onvoiceschanged = function () { loadVoices(); updateVoiceStatus(); };
    } catch (e) {}
  }

  // Narration is "intended" when audio isn't explicitly disabled and at least
  // one scene has spoken text. A voice is "missing" when speech is unsupported
  // or the OS/browser exposes no TTS voices at all.
  function narrationIntended() {
    if (DECK.audio && DECK.audio.enabled === false) return false;
    return SCENES.some(function (s) { return narrationText(s); });
  }
  function voiceMissing() { return !SPEECH_OK || VOICES.length === 0; }

  // Show the on-screen indicator only after playback has begun (voices enumerate
  // lazily, so checking earlier yields false positives) and while not muted.
  function updateVoiceStatus() {
    if (!els.voiceStatus) return;
    els.voiceStatus.classList.toggle(
      "show", started && !muted && narrationIntended() && voiceMissing());
  }

  var els = {};                    // cached DOM refs
  var sceneEls = [];               // per-scene { root, beats[], diagram, svg, edges[], edgeLabels[], plan }
  var idx = 0;
  var playing = false;
  var muted = false;
  var timers = [];
  var sceneStart = 0;              // performance.now() baseline for current scene
  var elapsedAtPause = 0;
  var advanceArmed = false;

  // ---- Setup -----------------------------------------------------------

  function $(sel) { return document.querySelector(sel); }

  function clearTimers() { timers.forEach(clearTimeout); timers = []; }

  function totalDurationMs() {
    return SCENES.reduce(function (a, s) { return a + sceneDurationMs(s); }, 0);
  }

  function sceneDurationMs(s) {
    if (typeof s.durationSec === "number") return s.durationSec * 1000;
    var target = (DECK.targetDurationSec || 150) * 1000;
    return Math.round(target / Math.max(1, SCENES.length));
  }

  // For a shared diagram source used across several scenes, each scene must hide
  // the tokens it (and later scenes) reveal, while leaving earlier scenes'
  // reveals visible. Returns hideTokens[] per scene index.
  function computeCumulative() {
    var allTokens = {};   // sourceKey -> Set of every token revealed by any scene
    SCENES.forEach(function (s) {
      if (!s.mermaid) return;
      var set = allTokens[s.mermaid] || (allTokens[s.mermaid] = {});
      (s.buildSteps || []).forEach(function (st) {
        (st.reveal || []).forEach(function (t) { set[t] = true; });
      });
    });
    var prior = {};       // sourceKey -> Set of tokens revealed by earlier scenes
    return SCENES.map(function (s) {
      if (!s.mermaid) return [];
      var key = s.mermaid;
      var seen = prior[key] || (prior[key] = {});
      var hide = Object.keys(allTokens[key]).filter(function (t) { return !seen[t]; });
      (s.buildSteps || []).forEach(function (st) {
        (st.reveal || []).forEach(function (t) { seen[t] = true; });
      });
      return hide;
    });
  }

  function buildDOM() {
    els.stage = $("#stage");
    els.progressFill = $("#progress-fill");
    els.ticks = $("#progress-ticks");
    els.counter = $("#scene-counter");
    els.startOverlay = $("#start-overlay");
    els.voiceStatus = $("#voice-status");

    var HIDE = computeCumulative();
    var total = totalDurationMs();
    var acc = 0;
    SCENES.forEach(function (scene, i) {
      var root = document.createElement("section");
      root.className = "scene" + (scene.mermaid ? "" : " no-diagram");
      root.setAttribute("data-kind", scene.kind || "content");
      root.id = "scene-" + (scene.id || i);

      var textWrap = document.createElement("div");
      textWrap.className = "scene-text";
      var beatEls = (scene.beats || []).map(function (beat) {
        var b = document.createElement("div");
        b.className = "beat beat--" + (beat.style || "body");
        b.setAttribute("data-anim", REDUCED ? "fade" : (beat.anim || "fade-up"));
        if ((beat.anim === "typewriter") && !REDUCED) {
          var span = document.createElement("span");
          span.className = "tw";
          span.innerHTML = beat.text;
          var n = (beat.text || "").replace(/<[^>]+>/g, "").length || 1;
          b.style.setProperty("--tw-steps", String(n));
          b.style.setProperty("--tw-dur", Math.min(2.4, Math.max(0.6, n * 0.05)) + "s");
          b.appendChild(span);
        } else {
          b.innerHTML = beat.text;
        }
        textWrap.appendChild(b);
        return b;
      });
      root.appendChild(textWrap);

      var diagram = null;
      if (scene.mermaid) {
        diagram = document.createElement("div");
        diagram.className = "scene-diagram";
        root.appendChild(diagram);
      }
      if (scene.caption) {
        var cap = document.createElement("div");
        cap.className = "scene-caption";
        cap.textContent = scene.caption;
        root.appendChild(cap);
      }

      els.stage.appendChild(root);
      sceneEls.push({ root: root, beats: beatEls, diagram: diagram, svg: null,
                      edges: [], edgeLabels: [], hideTokens: HIDE[i],
                      plan: buildScenePlan(scene) });

      // progress tick
      acc += sceneDurationMs(scene);
      if (i < SCENES.length - 1) {
        var tick = document.createElement("div");
        tick.className = "tick";
        tick.style.left = (100 * acc / total) + "%";
        els.ticks.appendChild(tick);
      }
    });
  }

  // Precompute beat times and build-step times for a scene.
  function buildScenePlan(scene) {
    var beats = scene.beats || [];
    var beatTimes = beats.map(function (b, i) {
      return typeof b.atMs === "number" ? b.atMs : i * BEAT_STAGGER;
    });
    var builds = (scene.buildSteps || []).map(function (step) {
      var at = typeof step.atMs === "number"
        ? step.atMs
        : (beatTimes[step.atBeat] != null ? beatTimes[step.atBeat] : 0);
      return { at: at, reveal: step.reveal || [], effect: step.effect || "appear" };
    });
    var lastEvent = Math.max(0,
      beatTimes.length ? beatTimes[beatTimes.length - 1] : 0,
      builds.reduce(function (m, b) { return Math.max(m, b.at); }, 0));
    return { beatTimes: beatTimes, builds: builds, lastEvent: lastEvent };
  }

  // ---- Mermaid rendering ----------------------------------------------

  function initMermaid() {
    if (!window.mermaid || typeof window.mermaid.initialize !== "function") return false;
    var cfg = Object.assign({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      htmlLabels: false,
      flowchart: { htmlLabels: false, curve: "basis", nodeSpacing: 45, rankSpacing: 55, padding: 12 },
      themeVariables: {
        fontFamily: "inherit",
        fontSize: "18px",
        lineColor: "#9db0cf",
        primaryColor: "#e8eef7",
        primaryTextColor: "#29417a",
        primaryBorderColor: "#4682b4",
        clusterBkg: "rgba(255,255,255,0.04)",
        clusterBorder: "#4682b4",
        titleColor: "#ffffff",
        edgeLabelBackground: "#16233f"
      }
    }, DECK.mermaidConfig || {});
    window.mermaid.initialize(cfg);
    return true;
  }

  function renderAll() {
    var jobs = SCENES.map(function (scene, i) {
      if (!scene.mermaid) return Promise.resolve();
      if (!window.mermaid || typeof window.mermaid.render !== "function") {
        sceneEls[i].diagram.innerHTML =
          '<div style="color:#ff9d9d;font-size:.9rem">Diagram unavailable (mermaid.js failed to load)</div>';
        return Promise.resolve();
      }
      var id = "mmd-" + i + "-" + Math.random().toString(36).slice(2);
      return window.mermaid.render(id, scene.mermaid).then(function (res) {
        var rec = sceneEls[i];
        rec.diagram.innerHTML = res.svg;
        rec.svg = rec.diagram.querySelector("svg");
        if (rec.svg) {
          rec.svg.removeAttribute("height");
          rec.svg.style.maxWidth = "100%";
          rec.svg.style.width = "100%";
          // max-height is governed by CSS (.scene-diagram svg) so the mobile
          // media query can shrink it; an inline value would override that.
          rec.edges = collectEdges(rec.svg);
          rec.edgeLabels = Array.prototype.slice.call(
            rec.svg.querySelectorAll(".edgeLabels .edgeLabel, .edgeLabel"));
        }
      }).catch(function (err) {
        sceneEls[i].diagram.innerHTML =
          '<div style="color:#ff9d9d;font-size:.9rem">Diagram error: ' +
          String(err && err.message || err) + "</div>";
      });
    });
    return Promise.all(jobs);
  }

  function collectEdges(svg) {
    var e = svg.querySelectorAll("path.flowchart-link");
    if (!e.length) e = svg.querySelectorAll(".edgePaths path, g.edgePaths path");
    return Array.prototype.slice.call(e);
  }

  // Resolve a reveal token to SVG elements within a scene record.
  function resolveToken(rec, token) {
    if (!rec.svg) return [];
    if (token.indexOf("edge:") === 0) {
      var n = parseInt(token.slice(5), 10);
      var out = [];
      if (rec.edges[n]) out.push(rec.edges[n]);
      if (rec.edgeLabels[n]) out.push(rec.edgeLabels[n]);
      return out;
    }
    // node first, then cluster/subgraph
    var sel = 'g.node[id*="-' + token + '-"], g.node[id$="-' + token + '"], ' +
              'g.node[id="' + token + '"], g.node#' + cssEsc(token);
    var nodes = Array.prototype.slice.call(rec.svg.querySelectorAll(sel));
    if (nodes.length) return nodes;
    var csel = 'g.cluster[id="' + token + '"], g.cluster[id$="' + token + '"], ' +
               'g.cluster[id*="-' + token + '"], g.cluster#' + cssEsc(token);
    return Array.prototype.slice.call(rec.svg.querySelectorAll(csel));
  }

  function cssEsc(s) {
    return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  // Elements to hide at the start of this scene (its own + future reveals on the
  // same diagram); earlier scenes' reveals are left visible.
  function managedElements(rec) {
    var set = new Set();
    (rec.hideTokens || []).forEach(function (tok) {
      resolveToken(rec, tok).forEach(function (el) { set.add(el); });
    });
    return set;
  }

  function isPath(el) { return el && el.tagName && el.tagName.toLowerCase() === "path"; }

  function hideManaged(rec) {
    if (!rec.svg) return;
    managedElements(rec).forEach(function (el) {
      el.classList.add("mm-hidden");
      el.classList.remove("revealed", "mm-pulse");
      el.style.transition = "";
      el.style.strokeDashoffset = "";
      el.style.strokeDasharray = "";
      var shape = el.querySelector ? el.querySelector(".mm-pulse") : null;
      if (shape) shape.classList.remove("mm-pulse");
      if (!isPath(el)) el.classList.add("mm-anim");
    });
  }

  function revealEls(els2, effect) {
    els2.forEach(function (el, i) {
      var delay = REDUCED ? 0 : i * REVEAL_STAGGER;
      var act = function () {
        el.classList.remove("mm-hidden");
        if (effect === "draw" && isPath(el)) {
          var len = 0;
          try { len = el.getTotalLength(); } catch (e) { len = 0; }
          el.style.opacity = "1";
          if (len && !REDUCED) {
            el.style.strokeDasharray = len;
            el.style.strokeDashoffset = len;
            el.getBoundingClientRect();           // reflow
            el.style.transition = "stroke-dashoffset .7s ease";
            el.style.strokeDashoffset = "0";
          } else {
            el.style.strokeDashoffset = "0";
          }
        } else {
          el.classList.add("mm-anim", "revealed");
        }
        if (effect === "pulse" && !REDUCED) {
          // Pulse the shape child, not the <g>: scaling the group's CSS transform
          // would clobber its SVG positioning transform.
          var shape = isPath(el) ? el : (el.querySelector("rect, polygon, circle, ellipse") || el);
          shape.classList.add("mm-pulse");
        }
      };
      if (delay) timers.push(setTimeout(act, delay)); else act();
    });
  }

  function revealToken(rec, tok, effect) { revealEls(resolveToken(rec, tok), effect); }

  // On phones the diagram is rendered larger than the viewport (so labels stay
  // legible) and its container scrolls. After a build step reveals elements,
  // pan that container so the newly-revealed elements are centred in view —
  // otherwise the highlighted part of a wide diagram can be off-screen.
  function isNarrow() {
    return !!(window.matchMedia && window.matchMedia("(max-width: 760px)").matches);
  }

  // Size a scene's diagram for the current viewport. On desktop the SVG fits
  // the column width. On phones, shrinking a wide diagram to the screen width
  // makes its labels unreadable, so we render it at a legible scale (≈0.6px per
  // design unit) — small diagrams still just fit the width, dense/wide ones grow
  // past the screen and become horizontally pannable. Capped so nothing becomes
  // absurdly large, and never taller than the available height. Must run while
  // the scene is visible (an inactive scene has zero width).
  function sizeDiagram(rec) {
    var svg = rec && rec.svg;
    if (!svg) return;
    if (!isNarrow()) {
      svg.style.width = "100%";
      svg.style.height = "";
      svg.style.maxWidth = "100%";
      return;
    }
    var vb = svg.viewBox && svg.viewBox.baseVal;
    if (!vb || !vb.width || !vb.height) return;
    var cont = rec.diagram;
    var cw = cont.clientWidth || (window.innerWidth - 40);
    if (!cw) return;
    var aspect = vb.width / vb.height;
    var TARGET = 0.6;                              // rendered px per design unit
    var w = Math.max(cw, vb.width * TARGET);
    w = Math.min(w, cw * 3);                       // don't over-zoom huge diagrams
    var maxH = window.innerHeight * 0.6;           // keep within the visible height
    if (w / aspect > maxH) w = maxH * aspect;
    w = Math.max(cw, w);                           // never narrower than the screen
    svg.style.width = Math.round(w) + "px";
    svg.style.height = "auto";
    svg.style.maxWidth = "none";
  }

  function focusDiagram(rec, list) {
    if (!isNarrow() || !rec.diagram || !list || !list.length) return;
    var cont = rec.diagram;
    if (cont.scrollWidth <= cont.clientWidth + 1 &&
        cont.scrollHeight <= cont.clientHeight + 1) return;
    var cr = cont.getBoundingClientRect();
    var minL = Infinity, minT = Infinity, maxR = -Infinity, maxB = -Infinity;
    list.forEach(function (el) {
      if (!el || !el.getBoundingClientRect) return;
      var r = el.getBoundingClientRect();
      if (!r.width && !r.height) return;
      minL = Math.min(minL, r.left); minT = Math.min(minT, r.top);
      maxR = Math.max(maxR, r.right); maxB = Math.max(maxB, r.bottom);
    });
    if (minL === Infinity) return;
    var left = cont.scrollLeft + ((minL + maxR) / 2 - cr.left) - cr.width / 2;
    var top = cont.scrollTop + ((minT + maxB) / 2 - cr.top) - cr.height / 2;
    left = Math.max(0, left); top = Math.max(0, top);
    try { cont.scrollTo({ left: left, top: top, behavior: REDUCED ? "auto" : "smooth" }); }
    catch (e) { cont.scrollLeft = left; cont.scrollTop = top; }
  }

  // ---- Playback --------------------------------------------------------

  function showBeat(rec, i) { if (rec.beats[i]) rec.beats[i].classList.add("is-in"); }
  function hideBeats(rec) { rec.beats.forEach(function (b) { b.classList.remove("is-in"); }); }

  function activate(i) {
    sceneEls.forEach(function (r, j) { r.root.classList.toggle("is-active", j === i); });
    updateCounter();
  }

  // Reveal everything up to `fromMs` instantly, schedule the rest. If `autoAdvance`
  // and not the last scene, arm advancing to the next scene.
  function runScene(i, fromMs, autoAdvance) {
    clearTimers();
    var rec = sceneEls[i];
    var scene = SCENES[i];
    var plan = rec.plan;
    if (REDUCED) { fromMs = Infinity; autoAdvance = false; }  // reveal instantly, no autoplay

    hideBeats(rec);
    hideManaged(rec);
    sizeDiagram(rec);   // the scene is now visible, so its width is measurable

    plan.beatTimes.forEach(function (t, bi) {
      if (t <= fromMs) showBeat(rec, bi);
      else timers.push(setTimeout(function () { showBeat(rec, bi); }, t - fromMs));
    });

    plan.builds.forEach(function (b) {
      var fire = function () {
        var targets = [];
        b.reveal.forEach(function (tok) {
          var found = resolveToken(rec, tok);
          revealEls(found, b.effect);
          targets = targets.concat(found);
        });
        focusDiagram(rec, targets);
      };
      if (b.at <= fromMs) fire();
      else timers.push(setTimeout(fire, b.at - fromMs));
    });

    sceneStart = performance.now() - fromMs;
    elapsedAtPause = fromMs;

    if (fromMs === 0 && !muted && SPEECH_OK && !REDUCED && scene.kind !== undefined) speak(scene);

    if (autoAdvance && i < SCENES.length - 1) armAdvance(i, fromMs, scene);
  }

  // Rough spoken duration so a scene holds long enough for its narration even
  // when the speech engine never fires onend (Chrome can swallow it silently).
  function estimateSpeechMs(scene) {
    var t = narrationText(scene);
    if (!t) return 0;
    var words = t.split(/\s+/).filter(Boolean).length;
    var rate = (DECK.audio && DECK.audio.rate) || 1;
    // ~2.4 words/sec is intentionally a touch slower than typical TTS so the
    // scene holds until narration finishes, plus a tail buffer.
    return (words / (2.4 * Math.max(0.5, rate))) * 1000 + 900;
  }

  // Auto-advance is timer-driven and does NOT depend on the speech callback, so
  // playback never stalls if narration is dropped or unavailable. speak()'s
  // onend may still advance early once the visuals have finished.
  function armAdvance(i, fromMs, scene) {
    advanceArmed = true;
    var hold = Math.max(sceneDurationMs(scene), sceneEls[i].plan.lastEvent + 1200);
    if (!muted && SPEECH_OK && !REDUCED && narrationText(scene)) {
      hold = Math.max(hold, estimateSpeechMs(scene));
    }
    timers.push(setTimeout(function () { doAdvance(i); }, Math.max(1200, hold - fromMs)));
  }

  function doAdvance(i) {
    if (!advanceArmed || i !== idx || !playing) return;
    advanceArmed = false;
    go(idx + 1);
  }

  function go(i) {
    if (i < 0 || i >= SCENES.length) return;
    if (SPEECH_OK) { stopKeepAlive(); window.speechSynthesis.cancel(); }
    idx = i;
    activate(i);
    if (playing) runScene(i, 0, true);
    else runScene(i, Infinity, false);   // paused: land fully revealed
    if (i === SCENES.length - 1 && playing) {
      // last scene: let it play out, then stop
    }
  }

  function play() {
    if (els.startOverlay) els.startOverlay.classList.add("hidden");
    if (playing) return;
    // boot() pre-renders the first scene with fromMs=Infinity (fully revealed,
    // no autoplay). Starting from that state must begin the scene fresh, else
    // the advance timer collapses to its floor and the first scene's narration
    // (which only fires at fromMs===0) is skipped.
    if (!isFinite(elapsedAtPause)) elapsedAtPause = 0;
    playing = true;
    started = true;
    setPlayIcon();
    // Voices often finish enumerating only after this first user gesture.
    loadVoices();
    updateVoiceStatus();
    runScene(idx, elapsedAtPause, true);
  }

  function pause() {
    if (!playing) return;
    playing = false;
    advanceArmed = false;
    elapsedAtPause = performance.now() - sceneStart;
    clearTimers();
    if (SPEECH_OK) { stopKeepAlive(); window.speechSynthesis.cancel(); }
    setPlayIcon();
  }

  function toggle() { playing ? pause() : play(); }

  function next() { pause(); go(Math.min(SCENES.length - 1, idx + 1)); }
  function prev() { pause(); go(Math.max(0, idx - 1)); }

  function replay() {
    if (SPEECH_OK) { stopKeepAlive(); window.speechSynthesis.cancel(); }
    idx = 0; elapsedAtPause = 0; playing = true;
    activate(0); setPlayIcon();
    if (els.startOverlay) els.startOverlay.classList.add("hidden");
    runScene(0, 0, true);
  }

  // ---- Narration -------------------------------------------------------

  function narrationText(scene) {
    if (scene.narration) return scene.narration;
    return (scene.beats || []).map(function (b) {
      return (b.text || "").replace(/<[^>]+>/g, "");
    }).join(". ");
  }

  var keepAlive = null;
  function stopKeepAlive() { if (keepAlive) { clearInterval(keepAlive); keepAlive = null; } }

  function speak(scene) {
    var text = narrationText(scene);
    if (!text) return;
    try { window.speechSynthesis.cancel(); } catch (e) {}
    stopKeepAlive();

    var u = new SpeechSynthesisUtterance(text);
    var hint = (DECK.audio && DECK.audio.voiceHint) || "en";
    var v = VOICES.filter(function (vc) {
      return vc.lang && vc.lang.toLowerCase().indexOf(hint.toLowerCase()) === 0;
    })[0];
    if (v) u.voice = v;
    u.rate = (DECK.audio && DECK.audio.rate) || 1;

    u.onstart = function () {
      // Chrome silently stops utterances after ~15s; a periodic pause/resume
      // keeps long narration going to the end.
      stopKeepAlive();
      keepAlive = setInterval(function () {
        if (!window.speechSynthesis.speaking) { stopKeepAlive(); return; }
        try { window.speechSynthesis.pause(); window.speechSynthesis.resume(); } catch (e) {}
      }, 9000);
    };
    // Pacing is driven solely by the armAdvance timer (sized to the larger of
    // the visual timeline and the estimated narration length), NOT by onend.
    // Browsers fire onend/onstart instantly when no voice actually speaks, which
    // would otherwise race the deck through every scene. Narration just plays
    // alongside and finishes within the timed window.
    u.onend = u.onerror = function () { stopKeepAlive(); };

    // Chrome drops an utterance queued in the same tick as cancel(); defer a
    // beat and resume() first to clear any stuck paused state.
    setTimeout(function () {
      try { window.speechSynthesis.resume(); } catch (e) {}
      try { window.speechSynthesis.speak(u); } catch (e) {}
    }, 60);
  }

  // ---- UI glue ---------------------------------------------------------

  function updateCounter() {
    if (els.counter) els.counter.textContent = (idx + 1) + " / " + SCENES.length;
    if (els.progressFill) {
      els.progressFill.style.transition = REDUCED ? "none" : "width .4s linear";
      els.progressFill.style.width = (100 * (idx + 1) / SCENES.length) + "%";
    }
  }

  function setPlayIcon() {
    var b = $("#btn-play");
    if (b) b.textContent = playing ? "⏸" : "▶";
  }

  function setMuteIcon() {
    var b = $("#btn-mute");
    if (b) b.textContent = muted ? "🔇" : "🔊";
  }

  function wireControls() {
    $("#btn-prev").addEventListener("click", prev);
    $("#btn-play").addEventListener("click", toggle);
    $("#btn-next").addEventListener("click", next);
    $("#btn-replay").addEventListener("click", replay);
    var mute = $("#btn-mute");
    if (mute) mute.addEventListener("click", function () {
      muted = !muted; setMuteIcon();
      if (muted && SPEECH_OK) { stopKeepAlive(); window.speechSynthesis.cancel(); }
      // Unmuting mid-scene starts narration for the current scene immediately.
      else if (!muted && playing) speak(SCENES[idx]);
      updateVoiceStatus();
    });
    var start = $("#start-btn");
    if (start) start.addEventListener("click", function () { idx = 0; activate(0); play(); });

    document.addEventListener("keydown", function (e) {
      if (e.code === "Space") { e.preventDefault(); toggle(); }
      else if (e.code === "ArrowRight") next();
      else if (e.code === "ArrowLeft") prev();
      else if (e.key === "r" || e.key === "R") replay();
    });

    if (REDUCED) {
      var hint = $("#reduced-hint");
      if (hint) hint.style.display = "inline";
    }

    // Re-fit the visible diagram when the viewport changes (rotation, resize).
    var resizeT;
    window.addEventListener("resize", function () {
      clearTimeout(resizeT);
      resizeT = setTimeout(function () { sizeDiagram(sceneEls[idx]); }, 150);
    });
  }

  // ---- Boot ------------------------------------------------------------

  function boot() {
    buildDOM();
    wireControls();
    setMuteIcon();
    activate(0);
    initMermaid();
    renderAll().then(function () {
      // hide all managed elements up front so nothing flashes before its scene
      sceneEls.forEach(hideManaged);
      activate(0);
      // First scene shown fully (under the start overlay) so the title is visible.
      runScene(0, Infinity, false);
      // Voices load asynchronously in some browsers.
      if (SPEECH_OK) window.speechSynthesis.getVoices();
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
