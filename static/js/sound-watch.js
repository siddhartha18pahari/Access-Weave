/* AccessWeave Sound Watch — visual + vibration alerts for sounds.

   For Deaf and hard-of-hearing users: the microphone listens for loud sounds
   (a doorbell, an alarm, a knock, a shout) and converts them into VISUAL alerts,
   vibration, and — when you are in another tab — a system notification.

   Runs in the background. Detection lives in an AudioWorklet on the browser's
   audio thread, which browsers do NOT throttle when a tab is hidden (unlike
   requestAnimationFrame and timers). So switching tabs does not stop the watch.

   Privacy: all analysis is on-device. No audio is recorded, stored, or uploaded;
   only a level number and "a sound ended" decision ever leave the audio thread.

   Safety: alerts use a single slow colour pulse, never a strobe (WCAG 2.3.1),
   and the pulse is disabled entirely under reduced motion. */
(function () {
  "use strict";

  const startBtn = document.getElementById("sw-start");
  const stopBtn = document.getElementById("sw-stop");
  const statusEl = document.getElementById("sw-status");
  const meterEl = document.getElementById("sw-meter");
  const logEl = document.getElementById("sw-log");
  const overlay = document.getElementById("sw-overlay");
  const overlayText = document.getElementById("sw-overlay-text");
  const sens = document.getElementById("sw-sensitivity");
  const notifyBtn = document.getElementById("sw-notify");
  const bgState = document.getElementById("sw-bg-state");
  const live = document.getElementById("aw-live");
  if (!startBtn) return;

  let ctx = null, node = null, stream = null, running = false, wakeLock = null;
  let starting = false, autoTimer = null;

  function status(msg) {
    if (statusEl) statusEl.textContent = msg;
    if (live) live.textContent = msg;
  }
  function vibrate(pattern) {
    if (navigator.vibrate) { try { navigator.vibrate(pattern); } catch (e) {} }
  }

  // --- System notifications: how an alert reaches you in another tab --------
  function canNotify() {
    return ("Notification" in window) && Notification.permission === "granted";
  }
  function refreshNotifyBtn() {
    if (!notifyBtn) return;
    if (!("Notification" in window)) { notifyBtn.hidden = true; return; }
    const granted = Notification.permission === "granted";
    notifyBtn.hidden = granted;
    notifyBtn.disabled = Notification.permission === "denied";
    if (Notification.permission === "denied") {
      notifyBtn.textContent = "Notifications blocked in browser settings";
    }
  }
  if (notifyBtn) {
    notifyBtn.addEventListener("click", async () => {
      try {
        await Notification.requestPermission();
      } catch (e) {}
      refreshNotifyBtn();
      status(canNotify()
        ? "Notifications are on. You'll be alerted even in another tab."
        : "Notifications are off. Alerts will still show on this page.");
    });
    refreshNotifyBtn();
  }

  // Android Chrome (and other mobile browsers) throw "Illegal constructor" for
  // `new Notification()` — there, notifications MUST go through the service
  // worker. Try that first, and if neither route works, say so rather than
  // leaving the user believing they'll be alerted in another tab.
  let notifyRoute = null;   // "sw" | "direct" | "none"
  async function notify(kind) {
    if (!canNotify() || document.visibilityState === "visible") return;
    const opts = { body: kind, tag: "aw-sound", renotify: true, silent: false };

    if (notifyRoute !== "direct" && "serviceWorker" in navigator) {
      try {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg && reg.showNotification) {
          await reg.showNotification("Sound detected", opts);
          notifyRoute = "sw";
          return;
        }
      } catch (e) { /* fall through to the direct constructor */ }
    }
    try {
      const n = new Notification("Sound detected", opts);
      n.onclick = () => { window.focus(); n.close(); };
      notifyRoute = "direct";
    } catch (e) {
      if (notifyRoute !== "none") {
        notifyRoute = "none";
        status("Your browser won't show notifications from a background tab. "
             + "Keep this tab visible to see alerts.");
      }
    }
  }

  // --- Screen wake lock: keeps a phone from sleeping mid-watch --------------
  async function acquireWakeLock() {
    if (!("wakeLock" in navigator)) return;
    try {
      wakeLock = await navigator.wakeLock.request("screen");
      wakeLock.addEventListener("release", () => { wakeLock = null; });
    } catch (e) { /* not fatal */ }
  }
  document.addEventListener("visibilitychange", () => {
    if (running && document.visibilityState === "visible" && !wakeLock) acquireWakeLock();
    if (bgState) {
      bgState.textContent = running
        ? (document.visibilityState === "visible"
            ? "Watching this tab."
            : "Watching in the background.")
        : "";
    }
  });

  function classify(durationMs, bursts) {
    if (bursts >= 3) return "A repeating sound — could be an alarm, a doorbell, or knocking.";
    if (durationMs > 2500) return "A continuous loud sound — could be an alarm, running water, or a vehicle.";
    if (durationMs > 700) return "A sustained sound — could be a voice calling or a bell.";
    return "A short sound — could be a knock, a clap, or something falling.";
  }

  function alert(kind) {
    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit", minute: "2-digit", second: "2-digit" });

    if (overlay) {
      overlayText.textContent = "Sound detected — " + kind;
      overlay.classList.add("on");
      setTimeout(() => overlay.classList.remove("on"), 2600);
    }
    vibrate([180, 90, 180]);
    notify(kind);
    status("Sound detected. " + kind);

    if (logEl) {
      const li = document.createElement("li");
      li.textContent = `${time} — ${kind}`;
      logEl.prepend(li);
      while (logEl.children.length > 12) logEl.removeChild(logEl.lastChild);
    }
  }

  async function start() {
    // `running` is only set after two awaits, so a user click can race the
    // ?auto=1 timer and open a second mic stream + AudioContext that never
    // gets cleaned up. Guard synchronously.
    if (running || starting) return;
    starting = true;
    if (autoTimer) { clearTimeout(autoTimer); autoTimer = null; }
    startBtn.disabled = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (e) {
      status("I couldn't use the microphone. Please allow microphone access, then press Start again.");
      startBtn.disabled = false;
      starting = false;
      return;
    }
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      // Browsers start an AudioContext suspended when it wasn't created from a
      // user gesture — which is exactly what happens on the ?auto=1 path used by
      // the voice command. Without this the worklet never runs and Sound Watch
      // would sit there claiming to listen while detecting nothing.
      if (ctx.state === "suspended") {
        try { await ctx.resume(); } catch (e) { /* handled below */ }
      }
      const workletUrl = (startBtn.dataset.workletUrl || "/static/js/sound-worklet.js");
      await ctx.audioWorklet.addModule(workletUrl);
    } catch (e) {
      // Older browsers without AudioWorklet: tell the truth rather than
      // pretending background watching works.
      status("This browser can't run Sound Watch in the background. "
           + "Chrome or Edge will keep watching while you're in another tab.");
      try { if (ctx) await ctx.close(); } catch (err) {}
      stream.getTracks().forEach((t) => t.stop());
      stream = null; ctx = null;
      startBtn.disabled = false;
      starting = false;
      return;
    }

    const src = ctx.createMediaStreamSource(stream);
    node = new AudioWorkletNode(ctx, "sound-watch");
    node.port.onmessage = (e) => {
      const d = e.data || {};
      if (d.type === "level") {
        if (meterEl) meterEl.style.width = Math.min(100, d.level * 400) + "%";
      } else if (d.type === "ready") {
        status("Watching for sounds. I'll alert you visually and with vibration — "
             + "including when you're in another tab.");
      } else if (d.type === "sound") {
        alert(classify(d.durationMs, d.bursts));
      }
    };
    if (sens) node.port.postMessage({ sensitivity: parseFloat(sens.value) });
    src.connect(node);
    // Keep the graph alive without making any sound of our own.
    const mute = ctx.createGain();
    mute.gain.value = 0;
    node.connect(mute).connect(ctx.destination);

    // Never claim to be listening if the audio graph isn't actually running.
    if (ctx.state !== "running") {
      status("Your browser paused the microphone because Sound Watch started on "
           + "its own. Press “Start watching” to begin.");
      try { node.disconnect(); } catch (e) {}
      stream.getTracks().forEach((t) => t.stop());
      try { await ctx.close(); } catch (e) {}
      stream = null; ctx = null; node = null;
      startBtn.hidden = false;
      startBtn.disabled = false;
      starting = false;
      return;
    }

    starting = false;
    running = true;
    startBtn.hidden = true;
    if (stopBtn) stopBtn.hidden = false;
    if (bgState) bgState.textContent = "Watching this tab.";
    acquireWakeLock();
    status("Listening… learning the room's normal sound level first.");
  }

  function stop() {
    running = false;
    starting = false;
    if (autoTimer) { clearTimeout(autoTimer); autoTimer = null; }
    if (node) { try { node.disconnect(); } catch (e) {} node = null; }
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    if (ctx) { try { ctx.close(); } catch (e) {} ctx = null; }
    if (wakeLock) { try { wakeLock.release(); } catch (e) {} wakeLock = null; }
    startBtn.hidden = false;
    startBtn.disabled = false;
    if (stopBtn) stopBtn.hidden = true;
    if (meterEl) meterEl.style.width = "0%";
    if (bgState) bgState.textContent = "";
    status("Sound Watch is off.");
  }

  startBtn.addEventListener("click", start);
  if (stopBtn) stopBtn.addEventListener("click", stop);
  if (sens) sens.addEventListener("input", () => {
    if (node) node.port.postMessage({ sensitivity: parseFloat(sens.value) });
  });

  const url = new URL(window.location.href);
  if (url.searchParams.get("auto") === "1") autoTimer = setTimeout(start, 400);

  // Deliberately NOT stopped on pagehide — the point is to keep watching.
  window.addEventListener("pagehide", (e) => { if (!e.persisted) stop(); });
})();
