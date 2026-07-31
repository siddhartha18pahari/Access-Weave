/* AccessWeave switch scanning & dwell selection.

   For people who can't use a mouse or a full keyboard. The Access Passport
   already offers "switch" and "dwell" as input modes; this implements them.

   SWITCH SCANNING: a highlight steps automatically through the controls on the
   page. When it reaches the one you want, you press your switch — any key, a
   click, or a game-controller button — to activate it. Most assistive switches
   present as a keyboard or a controller, so no driver is needed.

   DWELL: no pressing at all. Rest the pointer (or a head/eye tracker) on a
   control and it activates once the dwell time elapses, with a visible ring
   counting down so nothing happens by surprise.

   Both are off unless the passport asks for them, and both can be stopped at
   any time with Escape. Nothing here removes an existing way of working — it
   only adds another. */
(function () {
  "use strict";

  const passportEl = document.getElementById("aw-passport");
  let passport = {};
  try { passport = passportEl ? JSON.parse(passportEl.textContent) : {}; } catch (e) {}
  const modes = passport.input_modes || [];
  const live = document.getElementById("aw-live");

  const SEL = 'a[href], button:not([disabled]), input:not([type="hidden"]):not([disabled]),'
            + ' select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function speak(msg) {
    if (live) live.textContent = msg;
    if (window.AWTTS) window.AWTTS.speak(msg, { flush: true });
  }
  function visible(el) {
    if (el.hidden || el.closest("[hidden]")) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    return s.visibility !== "hidden" && s.display !== "none";
  }
  function targets() {
    return Array.from(document.querySelectorAll(SEL))
      .filter(visible)
      .filter((el) => !el.closest("#aw-palette[hidden]"));
  }
  function label(el) {
    const t = (el.getAttribute("aria-label") || el.innerText || el.value ||
               el.placeholder || el.title || "").replace(/\s+/g, " ").trim();
    return t.slice(0, 60) || el.tagName.toLowerCase();
  }

  /* ---------------- Switch scanning ---------------- */
  const scan = {
    on: false, items: [], i: 0, timer: null, step: 1200,

    start() {
      if (this.on) return;
      this.items = targets();
      if (!this.items.length) return;
      this.on = true;
      this.i = -1;
      document.documentElement.dataset.scanning = "true";
      speak("Switch scanning on. Press any key or click to choose the highlighted item. "
          + "Press Escape to stop.");
      if (this.startPads) this.startPads();
      this.next();
    },

    stop() {
      if (!this.on) return;
      this.on = false;
      clearTimeout(this.timer);
      if (this.stopPads) this.stopPads();
      this.clear();
      delete document.documentElement.dataset.scanning;
      speak("Switch scanning off.");
    },

    clear() {
      document.querySelectorAll(".aw-scan-active")
        .forEach((el) => el.classList.remove("aw-scan-active"));
    },

    next() {
      if (!this.on) return;
      this.clear();
      // Re-read targets periodically so the ring follows page changes.
      if (this.i < 0 || this.i >= this.items.length - 1) this.items = targets();
      this.i = (this.i + 1) % Math.max(1, this.items.length);
      const el = this.items[this.i];
      if (!el || !visible(el)) { this.timer = setTimeout(() => this.next(), 60); return; }
      el.classList.add("aw-scan-active");
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
      if (live) live.textContent = label(el);
      this.timer = setTimeout(() => this.next(), this.step);
    },

    choose() {
      const el = this.items[this.i];
      if (!el || this.activating) return;
      clearTimeout(this.timer);
      this.clear();
      speak("Chose " + label(el));
      // Give focus first so the action lands where a keyboard user would expect.
      try { el.focus({ preventScroll: true }); } catch (e) {}
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") {
        // Text fields: stop scanning so the user can type / use their AAC device.
        this.stop();
        return;
      }
      // Guard the synthetic click: our own capture-phase "switch press" listener
      // must let this one through, or the control would never actually fire.
      this.activating = true;
      try { el.click(); } finally {
        setTimeout(() => { this.activating = false; }, 0);
      }
      // Page may navigate; if not, resume after a beat.
      setTimeout(() => { if (this.on) { this.i = -1; this.next(); } }, 700);
    },
  };

  /* ---------------- Dwell selection ---------------- */
  const dwell = {
    on: false, el: null, timer: null, ring: null, ms: 1200,

    start() {
      if (this.on) return;
      this.on = true;
      this.ring = document.createElement("div");
      this.ring.className = "aw-dwell-ring";
      this.ring.setAttribute("aria-hidden", "true");
      document.body.appendChild(this.ring);
      document.addEventListener("pointermove", this.move, { passive: true });
      speak("Dwell selection on. Rest the pointer on a control to choose it. "
          + "Press Escape to stop.");
    },

    stop() {
      if (!this.on) return;
      this.on = false;
      this.cancel();
      document.removeEventListener("pointermove", this.move);
      if (this.ring) { this.ring.remove(); this.ring = null; }
      speak("Dwell selection off.");
    },

    cancel() {
      clearTimeout(this.timer);
      this.timer = null;
      this.el = null;
      if (this.ring) this.ring.classList.remove("on");
    },

    move: function (e) {
      const d = dwell;
      if (!d.on) return;
      const el = e.target.closest(SEL);
      if (!el || !visible(el)) { d.cancel(); return; }
      if (el === d.el) return;              // already counting down on this one
      d.cancel();
      d.el = el;
      const r = el.getBoundingClientRect();
      d.ring.style.left = (r.left + r.width / 2) + "px";
      d.ring.style.top = (r.top + r.height / 2) + "px";
      d.ring.style.animationDuration = d.ms + "ms";
      d.ring.classList.add("on");
      if (live) live.textContent = label(el);
      d.timer = setTimeout(() => {
        const target = d.el;
        d.cancel();
        if (!target) return;
        speak("Chose " + label(target));
        try { target.focus({ preventScroll: true }); } catch (err) {}
        target.click();
      }, d.ms);
    },
  };

  /* ---------------- Wiring ---------------- */
  // A switch press: any key, or a click anywhere that isn't already a control.
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (scan.on) { scan.stop(); return; }
      if (dwell.on) { dwell.stop(); return; }
    }
    if (!scan.on) return;
    // Let the palette and text fields work normally.
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    e.preventDefault();
    scan.choose();
  }, true);

  document.addEventListener("click", function (e) {
    if (!scan.on) return;
    if (scan.activating) return;                       // our own synthetic click
    if (e.target.closest("[data-scan-toggle]")) return; // let the toggle work
    e.preventDefault();
    e.stopPropagation();
    scan.choose();
  }, true);

  // Game controllers / adapted switches often present as gamepads.
  // The poll only runs while scanning is on — an always-on 60fps loop would
  // drain battery on every page for every user, most of whom never use a switch.
  let padPrev = Object.create(null);
  let padRaf = null;
  function pollPads() {
    if (!scan.on) { padRaf = null; return; }       // self-terminating
    const pads = navigator.getGamepads() || [];
    for (const p of pads) {
      if (!p) continue;
      for (let i = 0; i < p.buttons.length; i++) {
        const key = p.index + ":" + i;
        const pressed = p.buttons[i].pressed;
        if (pressed && !padPrev[key]) scan.choose();
        padPrev[key] = pressed;
      }
    }
    padRaf = requestAnimationFrame(pollPads);
  }
  scan.startPads = function () {
    if (!navigator.getGamepads || padRaf !== null) return;
    padPrev = Object.create(null);                 // don't inherit a held button
    padRaf = requestAnimationFrame(pollPads);
  };
  scan.stopPads = function () {
    if (padRaf !== null) { cancelAnimationFrame(padRaf); padRaf = null; }
  };

  // Toggle buttons (Display menu) + public API for the voice assistant.
  document.addEventListener("click", function (e) {
    const b = e.target.closest("[data-scan-toggle]");
    if (!b) return;
    const kind = b.dataset.scanToggle;
    if (kind === "switch") {
      scan.on ? scan.stop() : scan.start();
      b.setAttribute("aria-pressed", String(scan.on));
    } else {
      dwell.on ? dwell.stop() : dwell.start();
      b.setAttribute("aria-pressed", String(dwell.on));
    }
  });

  window.awScan = {
    startSwitch: () => scan.start(), stopSwitch: () => scan.stop(),
    startDwell: () => dwell.start(), stopDwell: () => dwell.stop(),
    setSpeed: (ms) => { scan.step = ms; dwell.ms = ms; },
    isScanning: () => scan.on, isDwelling: () => dwell.on,
  };

  // Honour the passport: if the user said they use a switch or dwell, offer it
  // immediately rather than making them find a setting.
  if (modes.includes("switch")) setTimeout(() => scan.start(), 1200);
  else if (modes.includes("dwell")) setTimeout(() => dwell.start(), 1200);
})();
