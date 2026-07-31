/* AccessWeave assists: keyboard shortcut sheet + focus mode.

   Shortcut sheet: press "?" anywhere to see every keyboard route through the
   app. Discoverability matters — a shortcut nobody knows about helps nobody.

   Focus mode: quiets the header, footer, and tips so only the task remains
   prominent. Cognitive support for anyone who finds a full page overwhelming;
   it dims rather than removes, so nothing becomes unreachable. */
(function () {
  "use strict";

  const live = document.getElementById("aw-live");
  const root = document.documentElement;
  function announce(m) {
    if (live) live.textContent = m;
    if (window.AWTTS) window.AWTTS.speak(m, { flush: true });
  }

  /* ---------------- Focus mode ---------------- */
  function focusOn() {
    try { return localStorage.getItem("aw:focus") === "on"; } catch (e) { return false; }
  }
  function applyFocus(on) {
    if (on) root.dataset.focusMode = "true";
    else delete root.dataset.focusMode;
    document.querySelectorAll('[data-aw="focus"]').forEach((b) =>
      b.setAttribute("aria-pressed", String(on)));
  }
  applyFocus(focusOn());

  window.awToggleFocus = function (force) {
    const on = typeof force === "boolean" ? force : !focusOn();
    try { localStorage.setItem("aw:focus", on ? "on" : "off"); } catch (e) {}
    applyFocus(on);
    announce(on ? "Focus mode on. Everything except your task is quieted."
                : "Focus mode off.");
  };

  document.addEventListener("click", function (e) {
    if (e.target.closest('[data-aw="focus"]')) window.awToggleFocus();
  });

  /* ---------------- Shortcut sheet ---------------- */
  const sheet = document.getElementById("aw-shortcuts");
  let opener = null;
  function openSheet() {
    if (!sheet) return;
    opener = document.activeElement;
    sheet.hidden = false;
    (sheet.querySelector("[data-shortcuts-close]") || sheet).focus();
  }
  function closeSheet() {
    if (!sheet || sheet.hidden) return;
    sheet.hidden = true;
    if (opener && document.contains(opener)) opener.focus();
    opener = null;
  }
  window.awShortcuts = openSheet;

  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-shortcuts-open]")) { e.preventDefault(); openSheet(); }
    if (e.target.closest("[data-shortcuts-close]") || e.target === sheet) closeSheet();
  });

  document.addEventListener("keydown", function (e) {
    const t = e.target;
    const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
                         t.isContentEditable);
    if (sheet && !sheet.hidden) {
      if (e.key === "Escape") { e.preventDefault(); closeSheet(); return; }
      if (e.key === "Tab") { e.preventDefault(); }   // single-button dialog
      return;
    }
    if (typing || e.ctrlKey || e.metaKey) return;

    if (e.key === "?" || (e.key === "/" && e.shiftKey)) {
      e.preventDefault(); openSheet(); return;
    }
    // Alt-based shortcuts stay clear of the browser's own bindings.
    if (!e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === "f") { e.preventDefault(); window.awToggleFocus(); }
    else if (k === "s") {
      e.preventDefault();
      if (window.awScan) window.awScan.isScanning()
        ? window.awScan.stopSwitch() : window.awScan.startSwitch();
    }
    else if (k === "d") {
      e.preventDefault();
      if (window.awScan) window.awScan.isDwelling()
        ? window.awScan.stopDwell() : window.awScan.startDwell();
    }
    else if (k === "r") {
      e.preventDefault();
      if (window.awSpeakGuide) window.awSpeakGuide();
    }
  });
})();
