/* AccessWeave command palette — Ctrl/Cmd+K.

   Every feature reachable from one keystroke and a few letters. This is the
   keyboard twin of the voice assistant: the same actions, the same names, so
   whichever input suits you reaches the same place.

   Implemented as an accessible combobox: arrow keys move a virtual cursor,
   aria-activedescendant reports it to screen readers, Escape closes and returns
   focus, and the dialog traps Tab. It is pure enhancement — everything here is
   also a normal link elsewhere in the page. */
(function () {
  "use strict";

  const COMMANDS = [
    { label: "Start a task", hint: "Speak, photograph, or paste something", href: "/tasks/new/", icon: "i-plus" },
    { label: "Look around", hint: "Camera describes what's in front of you", href: "/look/?auto=1", icon: "i-eye" },
    { label: "Conversation mode", hint: "Live captions of what they say", href: "/captions/?auto=1", icon: "i-monitor" },
    { label: "Sound Watch", hint: "See and feel alerts for sounds", href: "/soundwatch/?auto=1", icon: "i-bell" },
    { label: "Communicate", hint: "Quick phrases and speech", href: "/communication/", icon: "i-chat" },
    { label: "Find support", hint: "Assistive options that fit your goal", href: "/resources/", icon: "i-tool" },
    { label: "My tasks", hint: "Everything you've started", href: "/tasks/", icon: "i-folder" },
    { label: "My passport", hint: "How you like things shown", href: "/passports/", icon: "i-compass" },
    { label: "Privacy & data", hint: "Delete anything, anytime", href: "/privacy/", icon: "i-shield" },
    { label: "Home", hint: "Back to the main screen", href: "/", icon: "i-layers" },
    { label: "Turn on voice control", hint: "Or press Alt+V", act: "voice", icon: "i-mic" },
    { label: "Read this page aloud", hint: "Audio guide", act: "guide", icon: "i-speaker" },
    { label: "Light theme", act: "theme:light", icon: "i-sun" },
    { label: "Dark theme", act: "theme:dark", icon: "i-moon" },
    { label: "High contrast", act: "theme:high", icon: "i-sliders" },
    { label: "Bigger text", act: "text:+", icon: "i-sliders" },
    { label: "Smaller text", act: "text:-", icon: "i-sliders" },
    { label: "Focus mode", hint: "Quiet everything but the task", act: "focus", icon: "i-eye" },
    { label: "Switch scanning", hint: "Highlight steps through controls", act: "scan", icon: "i-repeat" },
    { label: "Dwell selection", hint: "Rest the pointer to choose", act: "dwell", icon: "i-compass" },
    { label: "Keyboard shortcuts", hint: "Press ? any time", act: "keys", icon: "i-book" },
  ];

  const root = document.getElementById("aw-palette");
  if (!root) return;
  const input = root.querySelector("#aw-palette-input");
  const list = root.querySelector("#aw-palette-list");
  const empty = root.querySelector("#aw-palette-empty");
  let items = [], cursor = 0, opener = null;

  const icon = (n) => `<svg class="icon" aria-hidden="true"><use href="#${n}"/></svg>`;

  function score(cmd, q) {
    if (!q) return 1;
    const hay = (cmd.label + " " + (cmd.hint || "")).toLowerCase();
    if (hay.startsWith(q)) return 3;
    if (cmd.label.toLowerCase().includes(q)) return 2;
    if (hay.includes(q)) return 1;
    return 0;
  }

  function render(q) {
    q = (q || "").trim().toLowerCase();
    items = COMMANDS.map((c) => ({ c, s: score(c, q) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .map((x) => x.c);
    cursor = 0;
    list.innerHTML = items.map((c, i) => `
      <li class="pal-item" id="pal-${i}" role="option" aria-selected="${i === 0}" data-i="${i}">
        <span class="pal-ico" aria-hidden="true">${icon(c.icon)}</span>
        <span class="pal-text"><strong>${c.label}</strong>${c.hint ? `<span class="pal-hint">${c.hint}</span>` : ""}</span>
      </li>`).join("");
    empty.hidden = items.length > 0;
    input.setAttribute("aria-activedescendant", items.length ? "pal-0" : "");
  }

  function move(d) {
    if (!items.length) return;
    cursor = (cursor + d + items.length) % items.length;
    [...list.children].forEach((li, i) => li.setAttribute("aria-selected", String(i === cursor)));
    input.setAttribute("aria-activedescendant", "pal-" + cursor);
    list.children[cursor].scrollIntoView({ block: "nearest" });
  }

  function run(cmd) {
    if (!cmd) return;
    close();
    if (cmd.href) { window.location.href = cmd.href; return; }
    const a = cmd.act || "";
    if (a === "voice") { document.getElementById("voice-fab")?.click(); return; }
    if (a === "guide") { if (window.awSpeakGuide) window.awSpeakGuide(); return; }
    if (a.startsWith("theme:") && window.awApplyTheme) { window.awApplyTheme(a.slice(6)); return; }
    if (a === "focus") { if (window.awToggleFocus) window.awToggleFocus(); return; }
    if (a === "scan") { if (window.awScan) window.awScan.startSwitch(); return; }
    if (a === "dwell") { if (window.awScan) window.awScan.startDwell(); return; }
    if (a === "keys") { if (window.awShortcuts) window.awShortcuts(); return; }
    if (a.startsWith("text:")) {
      document.querySelector(a === "text:+" ? '[data-aw="text-larger"]' : '[data-aw="text-smaller"]')?.click();
    }
  }

  function open() {
    opener = document.activeElement;
    root.hidden = false;
    root.classList.add("open");
    input.value = "";
    render("");
    input.focus();
  }
  function close() {
    root.classList.remove("open");
    root.hidden = true;
    if (opener && document.contains(opener)) opener.focus();
    opener = null;
  }

  document.addEventListener("keydown", function (e) {
    const k = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && k === "k") {
      e.preventDefault();
      root.hidden ? open() : close();
      return;
    }
    if (root.hidden) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") { e.preventDefault(); run(items[cursor]); }
    else if (e.key === "Tab") { e.preventDefault(); } // trap: single-field dialog
  });

  input.addEventListener("input", () => render(input.value));
  list.addEventListener("click", (e) => {
    const li = e.target.closest("[data-i]");
    if (li) run(items[+li.dataset.i]);
  });
  root.addEventListener("mousedown", (e) => { if (e.target === root) close(); });
  document.querySelectorAll("[data-palette-open]").forEach((b) =>
    b.addEventListener("click", open));
})();
