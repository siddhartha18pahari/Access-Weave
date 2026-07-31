/* AccessWeave Conversation Mode — live captions + spoken replies.

   For Deaf and hard-of-hearing users at a counter, clinic, or meeting:
   the other person speaks → their words appear as LARGE live captions;
   the user replies with quick phrases or typed text → spoken aloud (and
   showable full-screen). Recognition runs in the browser; the transcript
   is never stored — it lives only on this page and clears when you leave. */
(function () {
  "use strict";

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const startBtn = document.getElementById("cap-start");
  const stopBtn = document.getElementById("cap-stop");
  const clearBtn = document.getElementById("cap-clear");
  const bigger = document.getElementById("cap-bigger");
  const smaller = document.getElementById("cap-smaller");
  const out = document.getElementById("cap-out");
  const interim = document.getElementById("cap-interim");
  const statusEl = document.getElementById("cap-status");
  const live = document.getElementById("aw-live");
  if (!startBtn || !out) return;

  let rec = null, want = false, scale = 1.6;
  let paused = false;        // deliberately silenced while WE speak
  let failures = 0;          // consecutive immediate failures -> backoff
  let restartTimer = null;

  function status(msg) {
    if (statusEl) statusEl.textContent = msg;
    if (live) live.textContent = msg;
  }

  if (!SR) {
    startBtn.hidden = true;
    status("Live captions aren't supported in this browser. Chrome or Edge work best.");
    return;
  }

  function applyScale() { out.style.fontSize = scale + "rem"; if (interim) interim.style.fontSize = scale + "rem"; }
  applyScale();

  function addFinal(text) {
    const p = document.createElement("p");
    p.textContent = text;
    out.appendChild(p);
    out.scrollTop = out.scrollHeight;
  }

  function start() {
    // Take sole ownership of the microphone: a second continuous recognizer
    // makes both abort, which would look like captions randomly dying.
    if (window.awVoice && window.awVoice.suspendForMic()) {
      status("Voice control paused while captions are on.");
    }
    want = true;
    failures = 0;
    rec = new SR();
    rec.lang = document.documentElement.lang || "en";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e) => {
      let interimText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) { failures = 0; addFinal(r[0].transcript.trim()); }
        else interimText += r[0].transcript;
      }
      if (interim) interim.textContent = interimText;
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        want = false;
        status("I can't hear — microphone access is off. Please allow it and press Start.");
        startBtn.hidden = false; if (stopBtn) stopBtn.hidden = true;
        return;
      }
      // network / audio-capture / aborted: count it so we can back off rather
      // than spin, and tell the user instead of failing silently.
      failures++;
    };
    rec.onend = () => {
      // Do NOT restart while we are deliberately paused for our own speech —
      // otherwise the app immediately transcribes its own reply.
      if (!want || paused) return;
      clearTimeout(restartTimer);
      const delay = Math.min(4000, 200 * Math.pow(2, Math.max(0, failures - 1)));
      if (failures >= 4) {
        status("Captions keep dropping out. Check the microphone or your "
             + "connection, then press Start again.");
        want = false;
        startBtn.hidden = false; if (stopBtn) stopBtn.hidden = true;
        return;
      }
      restartTimer = setTimeout(() => {
        if (want && !paused) { try { rec.start(); } catch (err) {} }
      }, delay);
    };
    try { rec.start(); } catch (err) {}
    startBtn.hidden = true;
    if (stopBtn) stopBtn.hidden = false;
    status("Captions on — the other person's words will appear below.");
  }

  function stop() {
    want = false;
    paused = false;
    clearTimeout(restartTimer);
    if (rec) { try { rec.stop(); } catch (e) {} }
    if (window.awVoice) window.awVoice.resumeAfterMic();
    startBtn.hidden = false;
    if (stopBtn) stopBtn.hidden = true;
    if (interim) interim.textContent = "";
    status("Captions off.");
  }

  startBtn.addEventListener("click", start);
  if (stopBtn) stopBtn.addEventListener("click", stop);
  if (clearBtn) clearBtn.addEventListener("click", () => { out.innerHTML = ""; if (interim) interim.textContent = ""; });
  if (bigger) bigger.addEventListener("click", () => { scale = Math.min(3.2, scale + 0.25); applyScale(); });
  if (smaller) smaller.addEventListener("click", () => { scale = Math.max(1.0, scale - 0.25); applyScale(); });

  // While captioning, replies should not be transcribed as the partner's words:
  // pause recognition while our own speech (TTS) is playing, then resume.
  function pauseWhileSpeaking(ms) {
    if (!want || !rec) return;
    paused = true;
    clearTimeout(restartTimer);
    try { rec.stop(); } catch (err) {}
    restartTimer = setTimeout(() => {
      paused = false;
      if (want) { try { rec.start(); } catch (err) {} }
    }, ms);
  }
  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-phrase]") || e.target.closest("[data-partner-open]") ||
        e.target.closest('[data-aw="speak"]')) {
      pauseWhileSpeaking(2500);
    }
  });

  const url = new URL(window.location.href);
  if (url.searchParams.get("auto") === "1") setTimeout(start, 400);
  window.addEventListener("pagehide", stop);
})();
