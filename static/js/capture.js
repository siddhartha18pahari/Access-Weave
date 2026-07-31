/* AccessWeave input capture for people who can't (or shouldn't) paste text:
   - Voice input: speak your goal / describe the problem (Web Speech API).
   - On-device camera OCR: read a photo IN THE BROWSER (Tesseract.js). The image
     never leaves the device — only the extracted text is submitted.
   Both are progressive enhancements with clear spoken + on-screen fallbacks. */
(function () {
  "use strict";

  const live = document.getElementById("aw-live");
  function announce(msg) {
    if (live) live.textContent = msg;
    if (window.awSpeak && window.__awSpeech && window.__awSpeech.enabled) awSpeak(msg);
  }

  // --- One-shot voice input for a single field -----------------------------
  // (The global 🎙 Voice assistant handles hands-free, whole-page control;
  //  these buttons dictate into one field on demand when voice mode is off.)
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  document.querySelectorAll("[data-voice-target]").forEach(function (btn) {
    if (!SR) { btn.hidden = true; return; }
    const target = document.getElementById(btn.dataset.voiceTarget);
    btn.addEventListener("click", function () {
      const rec = new SR();
      rec.lang = document.documentElement.lang || "en";
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      btn.setAttribute("aria-pressed", "true");
      btn.textContent = "🎤 Listening…";
      announce("Listening. Please speak now.");
      rec.onresult = function (e) {
        const text = e.results[0][0].transcript;
        if (target) {
          target.value = (target.value ? target.value + " " : "") + text;
          target.focus();
        }
        announce("I heard: " + text);
      };
      rec.onerror = function (e) {
        announce("I couldn't hear that. You can try again or type instead.");
      };
      rec.onend = function () {
        btn.setAttribute("aria-pressed", "false");
        btn.textContent = btn.dataset.voiceLabel || "🎤 Speak";
      };
      try { rec.start(); } catch (err) { announce("Voice input is unavailable."); }
    });
  });

  // --- On-device camera / image OCR ---------------------------------------
  const fileInput = document.getElementById("image");
  const ocrStatus = document.getElementById("ocr-status");
  const sourceBox = document.getElementById("source_text");
  let tesseractLoading = null;

  function loadTesseract() {
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    if (tesseractLoading) return tesseractLoading;
    tesseractLoading = new Promise(function (resolve, reject) {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
      s.onload = function () { resolve(window.Tesseract); };
      s.onerror = function () { reject(new Error("offline")); };
      document.head.appendChild(s);
    });
    return tesseractLoading;
  }

  if (fileInput) {
    fileInput.addEventListener("change", async function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return;
      if (ocrStatus) ocrStatus.hidden = false;
      const set = (m) => { if (ocrStatus) ocrStatus.textContent = m; announce(m); };
      set("Reading the photo on your device…");
      let Tesseract;
      try {
        Tesseract = await loadTesseract();
      } catch (e) {
        set("On-device reading needs a connection the first time. You can still "
            + "submit the photo, or type/speak the text instead.");
        return;
      }
      try {
        const url = URL.createObjectURL(file);
        const { data } = await Tesseract.recognize(url, "eng", {
          logger: (info) => {
            if (info.status === "recognizing text") {
              set("Reading… " + Math.round(info.progress * 100) + "%");
            }
          },
        });
        URL.revokeObjectURL(url);
        const text = (data.text || "").trim();
        if (text && sourceBox) {
          sourceBox.value = text;
          // The image is read on-device; clear the file so only text is sent.
          fileInput.value = "";
          const conf = Math.round(data.confidence || 0);
          set("I read the label on your device. Please check it, then tap "
              + "“Make it accessible”. (Confidence about " + conf + "%. The photo "
              + "was not uploaded — only the text.)");
          sourceBox.focus();
        } else {
          set("I couldn't read clear text. Try a closer, well-lit photo, or "
              + "type/speak the text instead.");
        }
      } catch (e) {
        set("Something went wrong reading the photo. You can type or speak the text instead.");
      }
    });
  }
})();
