/* AccessWeave live "Look around" — real-time, on-device object detection.

   The user points the camera and hears what's in front of them: object names
   with rough position (left / ahead / right). Detection runs entirely in the
   browser (TensorFlow.js COCO-SSD) — no video or frame ever leaves the device.
   Speech uses the shared AWTTS engine (ElevenLabs when configured, else browser).
   Everything degrades gracefully: no camera, no model, or no support → a spoken
   explanation, never a silent failure. */
(function () {
  "use strict";

  const video = document.getElementById("live-video");
  const startBtn = document.getElementById("live-start");
  const stopBtn = document.getElementById("live-stop");
  const whatBtn = document.getElementById("live-what");
  const statusEl = document.getElementById("live-status");
  const live = document.getElementById("aw-live");
  if (!video || !startBtn) return;

  function say(msg, flush) {
    if (statusEl) statusEl.textContent = msg;
    if (live) live.textContent = msg;
    if (window.AWTTS) window.AWTTS.speak(msg, { flush: !!flush });
    else if ("speechSynthesis" in window) {
      if (flush) window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(msg));
    }
  }

  let model = null, stream = null, running = false, starting = false, loopTimer = null;
  let lastSpokenKey = "", lastFullSpeak = 0;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src; s.onload = resolve; s.onerror = () => reject(new Error("offline"));
      document.head.appendChild(s);
    });
  }

  // The first load pulls ~1.5 MB of libraries plus model weights and can take
  // 20-40 seconds on a slow connection. Silence would feel broken — especially
  // for a blind user — so we narrate progress and keep reassuring them.
  let heartbeat = null;
  function startHeartbeat() {
    const lines = [
      "Still preparing the camera. This only happens the first time.",
      "Almost ready. The model is downloading to your device.",
      "Nearly there — after this it starts instantly.",
    ];
    let i = 0;
    heartbeat = setInterval(() => {
      say(lines[Math.min(i, lines.length - 1)]);
      i++;
    }, 7000);
  }
  function stopHeartbeat() { if (heartbeat) { clearInterval(heartbeat); heartbeat = null; } }

  async function ensureModel() {
    if (model) return model;
    try {
      if (!window.cocoSsd) {
        say("Getting the camera ready. The first time takes up to a minute, "
          + "and everything stays on your device.");
        startHeartbeat();
        await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js");
        await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js");
      }
      model = await window.cocoSsd.load({ base: "lite_mobilenet_v2" });
      // Warm up once so the first real frame isn't the slow one.
      try {
        const warm = document.createElement("canvas");
        warm.width = warm.height = 128;
        await model.detect(warm);
      } catch (e) { /* warm-up is best-effort */ }
      return model;
    } finally {
      stopHeartbeat();
    }
  }

  function positionOf(pred, width) {
    const cx = pred.bbox[0] + pred.bbox[2] / 2;
    if (cx < width / 3) return "on your left";
    if (cx > (2 * width) / 3) return "on your right";
    return "ahead";
  }

  function describe(preds, width) {
    // group by "name position" and count
    const groups = {};
    preds.forEach((p) => {
      if (p.score < 0.55) return;
      const key = `${p.class}|${positionOf(p, width)}`;
      groups[key] = (groups[key] || 0) + 1;
    });
    const phrases = Object.entries(groups).map(([key, n]) => {
      const [name, pos] = key.split("|");
      const label = n > 1 ? `${n} ${name}s` : `a ${name}`;
      return `${label} ${pos}`;
    });
    return phrases;
  }

  async function detectOnce(speakAlways) {
    if (!model || video.readyState < 2) return;
    let preds = [];
    try { preds = await model.detect(video); } catch (e) { return; }
    const width = video.videoWidth || 640;
    const phrases = describe(preds, width);
    const key = phrases.slice().sort().join("; ");
    const now = (performance && performance.now) ? performance.now() : 0;

    if (!phrases.length) {
      if (speakAlways) say("I don't see anything I recognise right now. Try moving the camera slowly.", true);
      return;
    }
    // Speak when the scene changes, on demand, or at most every ~6s.
    if (speakAlways || key !== lastSpokenKey || now - lastFullSpeak > 6000) {
      lastSpokenKey = key;
      lastFullSpeak = now;
      say("I can see " + phrases.join(", ") + ".", speakAlways);
    }
  }

  async function start() {
    if (running || starting) return; // guard the async gap (auto-start + click)
    starting = true;
    startBtn.disabled = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } }, audio: false,
      });
    } catch (e) {
      say("I couldn't open the camera. Please allow camera access, then press Start again.", true);
      startBtn.disabled = false;
      starting = false;
      return;
    }
    video.srcObject = stream;
    await video.play().catch(() => {});
    try {
      await ensureModel();
    } catch (e) {
      say("The vision model needs an internet connection the first time. Please connect and try again.", true);
      starting = false;
      stop();
      return;
    }
    starting = false;
    running = true;
    startBtn.hidden = true;
    if (stopBtn) stopBtn.hidden = false;
    if (whatBtn) whatBtn.hidden = false;
    say("Camera on. Move it slowly and I'll tell you what I see.", true);
    const tick = async () => {
      if (!running) return;
      await detectOnce(false);
      loopTimer = setTimeout(tick, 1400);
    };
    tick();
  }

  function stop() {
    running = false;
    starting = false;
    stopHeartbeat();
    if (loopTimer) clearTimeout(loopTimer);
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    video.srcObject = null;
    startBtn.hidden = false;
    startBtn.disabled = false;
    if (stopBtn) stopBtn.hidden = true;
    if (whatBtn) whatBtn.hidden = true;
    say("Camera off.");
  }

  startBtn.addEventListener("click", start);
  if (stopBtn) stopBtn.addEventListener("click", stop);
  if (whatBtn) whatBtn.addEventListener("click", () => detectOnce(true));

  // Voice command hook: the global assistant can trigger a "what do you see".
  window.awLookWhatDoYouSee = () => detectOnce(true);
  window.awLookStart = start;

  // Auto-start when arrived here by voice ("look around").
  const url = new URL(window.location.href);
  if (url.searchParams.get("auto") === "1") setTimeout(start, 500);

  window.addEventListener("pagehide", stop);
})();
