/* AccessWeave progressive enhancement.
   The app is fully usable without this file. It adds: live personalization from
   the Access Passport, a quick personalization toolbar, speech output, the
   full-screen partner card, and offline support. */
(function () {
  "use strict";
  const root = document.documentElement;

  // --- Apply the Access Passport as design tokens + data attributes --------
  function applyPassport(p) {
    if (!p) return;
    const out = p.output || {};
    root.style.setProperty("--aw-text-scale", String(out.text_scale ?? 1));
    root.style.setProperty("--aw-target-size", (p.minimum_target_px ?? 44) + "px");
    if (out.contrast && out.contrast !== "system") root.dataset.contrast = out.contrast;
    root.dataset.reducedMotion = String(!!out.reduced_motion);
    root.dataset.readingRuler = String(!!out.reading_ruler);
    root.dataset.symbols = String(!!out.symbols_with_text);
    window.__awSpeech = { enabled: !!out.speech_enabled, rate: out.speech_rate ?? 1 };
  }

  const payloadEl = document.getElementById("aw-passport");
  if (payloadEl) {
    try { applyPassport(JSON.parse(payloadEl.textContent)); } catch (e) {}
  }

  // --- Personalization toolbar (persists to localStorage) ------------------
  function saveOverride(key, val) {
    try { localStorage.setItem("aw:" + key, val); } catch (e) {}
  }
  // Apply an explicit theme choice: system (respect OS) | light | dark | high.
  function applyTheme(theme) {
    if (!theme || theme === "system") delete root.dataset.contrast;
    else root.dataset.contrast = theme;
    reflectThemeButtons();
  }
  function currentTheme() {
    try {
      const saved = localStorage.getItem("aw:theme");
      if (saved && saved !== "system") return saved;  // 'system' is legacy -> light
    } catch (e) {}
    return root.dataset.contrast || "light";  // blue/white is the default
  }
  function effectiveIsDark() {
    // Light is the default; only an explicit Dark/High-contrast choice is dark.
    const dc = root.dataset.contrast;
    return dc === "dark" || dc === "high";
  }
  function reflectThemeButtons() {
    const cur = currentTheme();
    document.querySelectorAll("[data-theme]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.theme === cur)));
    // Top-bar sun/moon toggle mirrors the effective theme (glyph swap is CSS,
    // driven by aria-pressed).
    const t = document.querySelector("[data-theme-toggle]");
    if (t) {
      const dark = effectiveIsDark();
      t.setAttribute("aria-pressed", String(dark));
      t.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      t.title = dark ? "Light theme" : "Dark theme";
    }
  }
  window.awApplyTheme = function (theme) { saveOverride("theme", theme); applyTheme(theme); };

  function loadOverrides() {
    try {
      const ts = localStorage.getItem("aw:text-scale");
      if (ts) root.style.setProperty("--aw-text-scale", ts);
      const theme = localStorage.getItem("aw:theme");
      if (theme) applyTheme(theme);
      const rm = localStorage.getItem("aw:reduced-motion");
      if (rm) root.dataset.reducedMotion = rm;
    } catch (e) {}
    reflectThemeButtons();
    // Keep the Reduce-motion toggle's pressed state truthful on every load.
    document.querySelectorAll('[data-aw="motion"]').forEach((b) =>
      b.setAttribute("aria-pressed", String(root.dataset.reducedMotion === "true")));
  }
  loadOverrides();

  document.addEventListener("click", function (e) {
    const toggle = e.target.closest("[data-theme-toggle]");
    if (toggle) { window.awApplyTheme(effectiveIsDark() ? "light" : "dark"); return; }
    const themeBtn = e.target.closest("[data-theme]");
    if (themeBtn) { window.awApplyTheme(themeBtn.dataset.theme); return; }
    const btn = e.target.closest("[data-aw]");
    if (!btn) return;
    const action = btn.dataset.aw;
    if (action === "text-larger" || action === "text-smaller") {
      const cur = parseFloat(getComputedStyle(root).getPropertyValue("--aw-text-scale")) || 1;
      const next = Math.min(3, Math.max(0.8, cur + (action === "text-larger" ? 0.1 : -0.1)));
      root.style.setProperty("--aw-text-scale", next.toFixed(2));
      saveOverride("text-scale", next.toFixed(2));
    } else if (action === "motion") {
      const now = root.dataset.reducedMotion === "true" ? "false" : "true";
      root.dataset.reducedMotion = now;
      btn.setAttribute("aria-pressed", String(now === "true"));
      saveOverride("reduced-motion", now);
    } else if (action === "guide") {
      const now = !guideOn();
      saveOverride("guide", now ? "on" : "off");
      reflectGuideButton();
      if (now) { speak("Audio guide on. " + buildGuide()); }
      else { stopSpeak(); speak("Audio guide off."); }
    } else if (action === "speak") {
      speak(btn.dataset.text || btn.closest("[data-speakable]")?.dataset.speakable || "");
    } else if (action === "stop-speak") {
      stopSpeak();
    }
  });

  // --- Speech output (unified engine: ElevenLabs when configured, else browser)
  function speak(text) {
    if (!text) return;
    if (window.AWTTS) { window.AWTTS.speak(text, { flush: true }); return; }
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = (window.__awSpeech && window.__awSpeech.rate) || 1;
    window.speechSynthesis.speak(u);
  }
  function stopSpeak() {
    if (window.AWTTS) { window.AWTTS.stop(); return; }
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }
  window.awSpeak = speak;
  window.awStopSpeak = stopSpeak;

  // --- Audio guide: narrate where you are + what you can do, on each page ---
  // Strip emoji/symbols so speech doesn't read "waving hand", etc.
  function clean(s) {
    return (s || "")
      .replace(/[←-⇿⌀-➿⬀-⯿️\u{1F000}-\u{1FAFF}]/gu, "")
      .replace(/\s+/g, " ")
      .trim();
  }
  function buildGuide() {
    const h1 = document.querySelector("main h1");
    const where = clean(h1 ? h1.textContent : (document.title || "this page"));
    const seen = new Set();
    const actions = [];
    document.querySelectorAll(
      ".tile h2, main a.btn, main button.btn, nav.main a"
    ).forEach((el) => {
      const t = clean(el.textContent);
      if (t && t.length < 40 && !seen.has(t.toLowerCase())) {
        seen.add(t.toLowerCase());
        actions.push(t);
      }
    });
    let guide = where ? `You are on the ${where} page. ` : "";
    if (actions.length) guide += `You can: ${actions.slice(0, 7).join(", ")}. `;
    guide += "To act by voice, press the voice button or say help.";
    return guide;
  }
  function guideOn() {
    try { return localStorage.getItem("aw:guide") === "on"; } catch (e) { return false; }
  }
  window.awSpeakGuide = function () { speak(buildGuide()); };

  // Speak the guide on load when enabled — unless full Voice Mode is active
  // (that already narrates the page, so we avoid double speech).
  function voiceModeActive() {
    try { return sessionStorage.getItem("aw:voice") === "on"; } catch (e) { return false; }
  }
  if (guideOn() && !voiceModeActive()) {
    setTimeout(() => speak(buildGuide()), 700);
  }
  reflectGuideButton();
  function reflectGuideButton() {
    document.querySelectorAll('[data-aw="guide"]').forEach((b) =>
      b.setAttribute("aria-pressed", String(guideOn())));
  }

  // Auto-read the current task card when speech is enabled in the passport.
  // Skip if hands-free Voice Mode is active — voice.js owns speech there.
  const voiceModeOn = (function () {
    try { return sessionStorage.getItem("aw:voice") === "on"; } catch (e) { return false; }
  })();
  const autoCard = document.querySelector("[data-autospeak]");
  if (autoCard && window.__awSpeech && window.__awSpeech.enabled && !voiceModeOn) {
    setTimeout(() => speak(autoCard.dataset.autospeak), 400);
  }

  // --- Full-screen partner card (Communication Bridge) ---------------------
  // A real modal: focus moves in on open, Tab is trapped inside, and focus is
  // restored to the opener on close (Escape or the Close button).
  const partner = document.getElementById("partner-card");
  let partnerOpener = null;
  function closePartner() {
    if (!partner) return;
    partner.classList.remove("open");
    partner.setAttribute("aria-hidden", "true");
    if (partnerOpener && document.contains(partnerOpener)) partnerOpener.focus();
    partnerOpener = null;
  }
  document.addEventListener("click", function (e) {
    const open = e.target.closest("[data-partner-open]");
    if (open && partner) {
      const text = open.dataset.partnerOpen ||
        document.getElementById("composer")?.value || "";
      partner.querySelector("p").textContent = text || "…";
      partner.classList.add("open");
      partner.setAttribute("aria-hidden", "false");
      partnerOpener = open;
      const closeBtn = partner.querySelector("[data-partner-close]");
      (closeBtn || partner).focus();
      speak(text);
    }
    if (e.target.closest("[data-partner-close]") && partner) closePartner();
  });
  document.addEventListener("keydown", function (e) {
    if (!partner || !partner.classList.contains("open")) return;
    if (e.key === "Escape") { closePartner(); return; }
    if (e.key === "Tab") {
      // Trap: keep focus on the dialog's focusable controls.
      const focusables = partner.querySelectorAll(
        "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
      if (!focusables.length) { e.preventDefault(); partner.focus(); return; }
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      else if (!partner.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    }
  });

  // Composer: click a phrase to add it to the message box.
  document.addEventListener("click", function (e) {
    const p = e.target.closest("[data-phrase]");
    if (!p) return;
    const box = document.getElementById("composer");
    if (box) {
      box.value = (box.value ? box.value + " " : "") + p.dataset.phrase;
      box.focus();
    }
  });

  // --- Haptic feedback on task progress (phones) ----------------------------
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-haptic]") && navigator.vibrate) {
      try { navigator.vibrate(25); } catch (err) {}
    }
  });

  // --- Reading ruler follows the pointer -----------------------------------
  const ruler = document.querySelector(".ruler");
  if (ruler) {
    document.addEventListener("pointermove", function (e) {
      if (root.dataset.readingRuler === "true") {
        ruler.style.top = (e.clientY - 20) + "px";
      }
    });
  }

  // --- Service worker (offline) --------------------------------------------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    });
  }

  // --- Offline banner ------------------------------------------------------
  const banner = document.getElementById("offline-banner");
  function updateOnline() {
    if (banner) banner.hidden = navigator.onLine;
  }
  window.addEventListener("online", updateOnline);
  window.addEventListener("offline", updateOnline);
  updateOnline();
})();
