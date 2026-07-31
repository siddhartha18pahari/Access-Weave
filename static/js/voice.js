/* AccessWeave global voice assistant.

   One persistent voice control for the WHOLE app. Turn it on once and drive
   everything by speaking:
     • Navigate:   "home", "new task", "communicate", "resources", "passport",
                   "privacy", "my tasks", "log out", "go back".
     • Read:       "read the page", "repeat".
     • Adjust:     "bigger text", "smaller text", "high contrast".
     • In a task:  "next", "back", "simpler", "read the warning", "status",
                   "finish", "stop".
     • Create:     speak your goal, then say "go".
     • Anytime:    "help", "stop", "turn off voice".

   Reliability first: TTS is queued so nothing cuts off; recognition runs
   continuously and auto-restarts; state persists across page loads; and every
   spoken command has an equivalent on-screen control — nothing is voice-only.
*/
(function () {
  "use strict";

  const VKEY = "aw:voice";
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const live = document.getElementById("aw-live");
  const btn = document.getElementById("voice-fab");
  const status = document.getElementById("voice-fab-status");

  // ---------- Text-to-speech (delegates to the unified AWTTS engine, which
  //            uses ElevenLabs when configured and the browser voice otherwise).
  const tts = {
    speak(text, flush) {
      if (window.AWTTS) window.AWTTS.speak(text, { flush: !!flush });
      else if ("speechSynthesis" in window && text) {
        if (flush) window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(String(text)));
      }
    },
    stop() {
      if (window.AWTTS) window.AWTTS.stop();
      else if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    },
  };
  function say(msg, flush) { if (msg) tts.speak(msg, flush); if (live) live.textContent = msg || ""; }

  // ---------- State ----------
  function isOn() { try { return sessionStorage.getItem(VKEY) === "on"; } catch (e) { return false; } }
  function setOn(v) { try { sessionStorage.setItem(VKEY, v ? "on" : "off"); } catch (e) {} window.__awVoiceMode = v; }
  window.__awVoiceMode = isOn();

  // ---------- Continuous recognition ----------
  let rec = null, want = false, timer = null;
  function startListening(onCmd) {
    if (!SR) return false;
    want = true;
    rec = new SR();
    rec.lang = document.documentElement.lang || "en";
    rec.continuous = true;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const r = e.results[e.results.length - 1];
      if (r && r.isFinal) { const s = r[0].transcript.trim().toLowerCase(); if (s) onCmd(s); }
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        want = false;
        say("I can't hear you — microphone access is off. You can use the buttons instead.");
        reflect(false, "mic blocked");
      }
    };
    rec.onend = () => { if (want) { clearTimeout(timer); timer = setTimeout(() => { try { rec.start(); } catch (e) {} }, 300); } };
    try { rec.start(); } catch (e) {}
    return true;
  }
  function stopListening() { want = false; clearTimeout(timer); if (rec) { try { rec.stop(); } catch (e) {} } }

  const has = (s, words) => words.some((w) => s.includes(w));

  // ---------- Page context ----------
  const player = document.getElementById("voice-data");
  const vform = document.querySelector("form[data-voice-submit]");
  const root = document.documentElement;

  function navigate(path) { window.location.href = path; }

  function readPage() {
    const main = document.getElementById("main");
    const text = main ? main.innerText.replace(/\s+\n/g, "\n").replace(/\n{2,}/g, ". ").trim() : "";
    say(text ? text.slice(0, 1200) : "There's nothing to read here.", true);
  }

  // Operate ANY on-screen control by its visible text — makes the whole UI
  // voice-operable, not just the pre-defined commands.
  function clickByText(label) {
    label = (label || "").trim().toLowerCase().replace(/[.?!]+$/, "");
    if (!label) return false;
    const els = Array.from(document.querySelectorAll(
      'main a, main button, main [role="button"], .tile, .phrase, .voice-fab'));
    let best = null, bestLen = Infinity;
    for (const el of els) {
      if (el.offsetParent === null && el !== document.activeElement) continue; // visible only
      const t = (el.innerText || el.textContent || el.getAttribute("aria-label") || "").trim().toLowerCase();
      if (t && t.includes(label) && t.length < bestLen) { best = el; bestLen = t.length; }
    }
    if (best) {
      say("Opening " + (best.innerText || best.textContent || "it").trim().slice(0, 40) + ".");
      best.click();
      return true;
    }
    say(`I couldn't find "${label}" on this page.`, true);
    return true;
  }

  function scrollCmd(cmd) {
    if (has(cmd, ["scroll down", "page down", "further down", "keep reading"])) { window.scrollBy({ top: window.innerHeight * 0.8, behavior: "smooth" }); return true; }
    if (has(cmd, ["scroll up", "page up", "back up"])) { window.scrollBy({ top: -window.innerHeight * 0.8, behavior: "smooth" }); return true; }
    if (has(cmd, ["scroll to top", "top of page", "go to top"])) { window.scrollTo({ top: 0, behavior: "smooth" }); return true; }
    if (has(cmd, ["scroll to bottom", "bottom of page", "go to bottom"])) { window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); return true; }
    return false;
  }

  function recall() {
    fetch("/api/recent/", { headers: { "X-Requested-With": "fetch" } })
      .then((r) => r.json())
      .then((d) => say(d.summary || "You have no recent tasks.", true))
      .catch(() => say("I couldn't reach your recent tasks right now.", true));
  }

  function adjust(cmd) {
    if (has(cmd, ["bigger", "larger text", "increase text", "zoom in"])) {
      const c = parseFloat(getComputedStyle(root).getPropertyValue("--aw-text-scale")) || 1;
      const n = Math.min(3, c + 0.15); root.style.setProperty("--aw-text-scale", n.toFixed(2));
      try { localStorage.setItem("aw:text-scale", n.toFixed(2)); } catch (e) {}
      say("Bigger text."); return true;
    }
    if (has(cmd, ["smaller", "decrease text", "zoom out"])) {
      const c = parseFloat(getComputedStyle(root).getPropertyValue("--aw-text-scale")) || 1;
      const n = Math.max(0.8, c - 0.15); root.style.setProperty("--aw-text-scale", n.toFixed(2));
      try { localStorage.setItem("aw:text-scale", n.toFixed(2)); } catch (e) {}
      say("Smaller text."); return true;
    }
    if (has(cmd, ["high contrast", "more contrast"])) {
      if (window.awApplyTheme) window.awApplyTheme("high");
      say("High contrast on."); return true;
    }
    if (has(cmd, ["dark mode", "dark theme"])) {
      if (window.awApplyTheme) window.awApplyTheme("dark");
      say("Dark theme on."); return true;
    }
    if (has(cmd, ["light mode", "light theme", "normal contrast", "less contrast"])) {
      if (window.awApplyTheme) window.awApplyTheme("light");
      say("Light theme on."); return true;
    }
    if (has(cmd, ["system theme", "default theme", "match my system"])) {
      if (window.awApplyTheme) window.awApplyTheme("system");
      say("Matching your system theme."); return true;
    }
    return false;
  }

  function globalCommand(cmd) {
    if (has(cmd, ["stop", "quiet", "shush", "silence", "be quiet"])) { tts.stop(); say("Okay."); return true; }
    if (has(cmd, ["turn off voice", "voice off", "stop voice", "disable voice"])) { deactivate(); return true; }
    if (has(cmd, ["help", "what can i say", "commands"])) {
      say("You can say: new task, look around, conversation mode, sound watch, "
        + "communicate, resources, my tasks, passport, or home. Say click, then "
        + "any button name, to press it. Say read the page, scroll down, bigger "
        + "text, high contrast, or what have I done. In a task, say next, repeat, "
        + "simpler, or finish. Say turn off voice to stop.", true);
      return true;
    }
    if (has(cmd, ["read the page", "read this page", "read page", "read everything"])) { readPage(); return true; }
    // Audio guide (narrate where you are + what you can do).
    if (has(cmd, ["turn on audio guide", "audio guide on", "start narrating", "guide me through"])) {
      try { localStorage.setItem("aw:guide", "on"); } catch (e) {}
      if (window.awSpeakGuide) window.awSpeakGuide();
      return true;
    }
    if (has(cmd, ["turn off audio guide", "audio guide off", "stop narrating", "stop guiding"])) {
      try { localStorage.setItem("aw:guide", "off"); } catch (e) {}
      say("Audio guide off."); return true;
    }
    if (has(cmd, ["guide me", "describe the page", "narrate", "where am i"])) {
      if (window.awSpeakGuide) window.awSpeakGuide();
      return true;
    }
    // Alternative input + focus (the passport's switch/dwell modes).
    if (has(cmd, ["switch scanning", "start scanning", "scan the page", "switch mode"])) {
      if (window.awScan) { window.awScan.startSwitch(); } return true;
    }
    if (has(cmd, ["stop scanning", "stop switch"])) {
      if (window.awScan) { window.awScan.stopSwitch(); } return true;
    }
    if (has(cmd, ["dwell", "hover to click", "rest to click"])) {
      if (window.awScan) { window.awScan.startDwell(); } return true;
    }
    if (has(cmd, ["focus mode", "hide distractions", "quiet the page"])) {
      if (window.awToggleFocus) { window.awToggleFocus(true); } return true;
    }
    if (has(cmd, ["exit focus", "show everything", "turn off focus"])) {
      if (window.awToggleFocus) { window.awToggleFocus(false); } return true;
    }
    if (has(cmd, ["shortcuts", "keyboard help", "what are the shortcuts"])) {
      if (window.awShortcuts) { window.awShortcuts(); } return true;
    }
    if (adjust(cmd)) return true;

    // Navigation
    if (has(cmd, ["log out", "sign out", "logout"])) {
      const f = document.querySelector('form[action$="/logout/"]');
      if (f) { say("Logging out."); f.submit(); } else say("I couldn't find log out.");
      return true;
    }
    if (has(cmd, ["new task", "start a task", "start task", "create task", "new"])) { say("Opening new task."); navigate("/tasks/new/"); return true; }
    if (has(cmd, ["my tasks", "show tasks", "task list", "open tasks"])) { say("Opening your tasks."); navigate("/tasks/"); return true; }
    // Live "Look around" (camera object detection).
    if (has(cmd, ["what do you see", "what's there", "whats there", "describe what you see"])) {
      if (window.awLookWhatDoYouSee) { window.awLookWhatDoYouSee(); }
      else { say("Opening look around."); navigate("/look/?auto=1"); }
      return true;
    }
    if (has(cmd, ["look around", "what's in front", "whats in front", "describe my surroundings", "use the camera", "look mode"])) {
      say("Opening look around."); navigate("/look/?auto=1"); return true;
    }
    if (has(cmd, ["caption", "conversation mode", "what are they saying", "live transcript"])) {
      say("Opening conversation mode."); navigate("/captions/?auto=1"); return true;
    }
    if (has(cmd, ["sound watch", "watch for sounds", "alert me to sounds", "listen for sounds"])) {
      say("Opening sound watch."); navigate("/soundwatch/?auto=1"); return true;
    }
    if (has(cmd, ["communicate", "communication", "talk for me", "phrases"])) { say("Opening the communication bridge."); navigate("/communication/"); return true; }
    if (has(cmd, ["resource", "find help", "find support"])) { say("Opening resources."); navigate("/resources/"); return true; }
    if (has(cmd, ["passport", "my settings", "preferences", "my profile"])) { say("Opening your passport."); navigate("/passports/"); return true; }
    if (has(cmd, ["privacy", "my data", "delete my data"])) { say("Opening privacy."); navigate("/privacy/"); return true; }
    if (has(cmd, ["home", "main menu", "start over", "go home"])) { say("Going home."); navigate("/"); return true; }

    // Session recall (spoken summary of recent activity).
    if (has(cmd, ["what have i done", "recent task", "my history", "my activity", "recap", "remind me what"])) { recall(); return true; }
    // Scrolling.
    if (scrollCmd(cmd)) return true;
    // Generic "click / open / press <name>" — operate any visible control.
    const m = cmd.match(/\b(?:click|press|open|select|choose|tap|activate|go to)\s+(.+)/);
    if (m) return clickByText(m[1]);
    return false;
  }

  function playerCommand(cmd) {
    const step = parseInt(player.dataset.step, 10);
    const total = parseInt(player.dataset.total, 10);
    const base = player.dataset.base;
    const speakable = player.dataset.speakable || "";
    if (has(cmd, ["repeat", "again", "read again", "say again", "read it", "read the step"])) { say(speakable, true); return true; }
    if (has(cmd, ["where", "status", "which step", "what step"])) { say(`Step ${step + 1} of ${total}.`, true); return true; }
    if (has(cmd, ["simpler", "simple", "plain", "easier"])) { say("Making it simpler."); navigate(`${base}?step=${step}&simplify=1&voice=1`); return true; }
    if (has(cmd, ["warning", "danger", "limit", "caution"])) {
      const w = document.querySelector(".card.type-warning");
      say(w ? "Warning. " + w.textContent.replace(/\s+/g, " ").trim() : "No separate warning on this step.", true);
      return true;
    }
    if (has(cmd, ["back", "previous", "last step", "go back a step"])) {
      if (step > 0) navigate(`${base}?step=${step - 1}&voice=1`); else say("You're on the first step.", true);
      return true;
    }
    if (has(cmd, ["next", "continue", "forward", "go on", "proceed"])) {
      if (step < total - 1) navigate(`${base}?step=${step + 1}&voice=1`);
      else say("This is the last step. Say finish to complete.", true);
      return true;
    }
    if (has(cmd, ["finish", "complete", "done", "mark done", "end task"])) {
      const b = document.getElementById("voice-finish");
      if (b) { say("Finishing."); b.click(); } else if (step < total - 1) navigate(`${base}?step=${step + 1}&voice=1`);
      return true;
    }
    return false;
  }

  function formCommand(cmd) {
    const bare = cmd.trim().replace(/[.?!]+$/, "");
    // Submit only on an explicit, unambiguous trigger — never a substring, so a
    // goal like "go to the pharmacy" is dictated, not submitted.
    if (bare === "go" || bare === "okay go" || bare === "ok go" ||
        has(cmd, ["make it accessible", "build it", "submit the form", "i'm ready", "that's it"])) {
      setOn(true); say("Working on it."); vform.submit(); return true;
    }
    const goal = document.getElementById("goal");
    if (bare === "clear" || bare === "start over") {
      if (goal) goal.value = "";
      say("Cleared. Speak your goal."); return true;
    }
    if (goal) { goal.value = cmd; say("I heard: " + cmd + ". Say go when you're ready."); return true; }
    return false;
  }

  function route(cmd) {
    if (player && playerCommand(cmd)) return;
    // On the task-creation form, DICTATION WINS: whatever the user says becomes
    // their goal, so goals like "help me cook dinner" or "renew my bus pass"
    // are never hijacked by the global "help" / "new" / "home" matchers.
    // A few explicit escape hatches stay available while dictating.
    if (vform) {
      const bare = cmd.trim().replace(/[.?!]+$/, "");
      if (bare === "stop" || bare === "quiet") { tts.stop(); say("Okay."); return; }
      if (has(cmd, ["turn off voice", "voice off", "stop voice", "disable voice"])) { deactivate(); return; }
      if (bare === "help" || has(cmd, ["what can i say"])) {
        say("Speak your goal in your own words. Then say: go. You can also say "
          + "clear, or say click and a button name, or turn off voice.", true);
        return;
      }
      if (/^(?:click|press|open)\s+/.test(bare)) { if (globalCommand(cmd)) return; }
      if (formCommand(cmd)) return;
    }
    if (globalCommand(cmd)) return;
    say("I didn't catch that. Say help for a list of commands.");
  }

  // ---------- UI reflect ----------
  function reflect(on, note) {
    if (btn) { btn.setAttribute("aria-pressed", String(on)); btn.classList.toggle("listening", on); }
    if (status) status.textContent = on ? "Voice on" : (note || "Voice");
  }

  function greet() {
    if (player) {
      const step = parseInt(player.dataset.step, 10), total = parseInt(player.dataset.total, 10);
      say(`Voice on. Step ${step + 1} of ${total}.`);
      tts.speak(player.dataset.speakable || "");
      tts.speak("Say next, repeat, simpler, or finish.");
    } else if (vform) {
      say("Voice on. Speak your goal, then say: go.");
    } else {
      const h1 = document.querySelector("main h1");
      say("Voice on. " + (h1 ? h1.textContent + ". " : "") + "Say a command, or say help.");
    }
  }

  function activate(announce) {
    setOn(true); reflect(true);
    if (announce !== false) greet();
    const ok = startListening(route);
    if (!ok) say("Voice commands aren't supported in this browser, but every button still works.");
  }
  function deactivate() { setOn(false); stopListening(); tts.stop(); reflect(false); say("Voice off."); }

  if (btn) btn.addEventListener("click", () => { isOn() ? deactivate() : activate(); });

  // Global keyboard shortcut: Alt+V toggles voice anywhere.
  document.addEventListener("keydown", (e) => {
    if (e.altKey && (e.key === "v" || e.key === "V")) { e.preventDefault(); isOn() ? deactivate() : activate(); }
  });

  // Only one feature may own the microphone at a time. Live captions call these
  // so two continuous recognizers never fight over it (which aborts both).
  let suspendedByOther = false;
  window.awVoice = {
    suspendForMic() {
      if (!isOn()) return false;
      suspendedByOther = true;
      stopListening();
      tts.stop();
      reflect(false, "paused");
      return true;
    },
    resumeAfterMic() {
      if (!suspendedByOther) return;
      suspendedByOther = false;
      if (isOn()) { reflect(true); startListening(route); }
    },
  };

  // Auto-resume across navigation (persisted), or when a step link carries ?voice=1.
  const url = new URL(window.location.href);
  if (isOn() || url.searchParams.get("voice") === "1") {
    reflect(true);
    setTimeout(() => activate(true), 300);
  } else {
    reflect(false);
  }
})();
