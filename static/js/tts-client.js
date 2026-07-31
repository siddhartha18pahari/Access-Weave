/* AccessWeave unified text-to-speech.

   One voice engine for the whole app, exposed as window.AWTTS.speak() / .stop().
   Prefers high-quality ElevenLabs audio (proxied through the server so the API
   key never reaches the browser) and falls back instantly to the browser's
   built-in speech synthesis if that's unavailable or fails. Output is queued so
   long cards read smoothly without cutting off. Voice output therefore always
   works — with or without a paid key. */
(function () {
  "use strict";

  function cookie(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? decodeURIComponent(m.pop()) : "";
  }
  const httpEnabled = () => document.body && document.body.dataset.tts === "on";
  const rate = () => (window.__awSpeech && window.__awSpeech.rate) || 1;

  const engine = {
    q: [],
    busy: false,
    audio: null,
    gen: 0,           // bumped by stop(): anything from an older generation is stale
    aborter: null,    // cancels an in-flight synthesis request on stop()

    speak(text, opts) {
      opts = opts || {};
      if (!text) return;
      if (opts.flush) this.stop();
      this.q.push(String(text));
      if (!this.busy) this._next();
    },

    stop() {
      this.q = [];
      this.busy = false;
      this.gen++;
      if (this.aborter) { try { this.aborter.abort(); } catch (e) {} this.aborter = null; }
      if (this.audio) { try { this.audio.pause(); } catch (e) {} this.audio = null; }
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    },

    _next() {
      const text = this.q.shift();
      if (text === undefined) { this.busy = false; return; }
      this.busy = true;
      if (httpEnabled()) {
        // Capture the generation: if stop()/flush happened while the request was
        // in flight, this failure belongs to a cancelled utterance and must NOT
        // fall back to speaking the old text over whatever is playing now.
        const myGen = this.gen;
        this._speakHttp(text).catch(() => {
          if (myGen === this.gen) this._speakBrowser(text, myGen);
        });
      } else {
        this._speakBrowser(text, this.gen);
      }
    },

    async _speakHttp(text) {
      const myGen = this.gen;
      this.aborter = new AbortController();
      const body = new URLSearchParams({ text });
      const res = await fetch("/api/tts/", {
        method: "POST",
        headers: { "X-CSRFToken": cookie("csrftoken"),
                   "Content-Type": "application/x-www-form-urlencoded" },
        body,
        signal: this.aborter.signal,
      });
      if (myGen !== this.gen) return; // stopped while in flight — discard
      if (res.status !== 200) { this._speakBrowser(text); return; } // 204 => fallback
      const blob = await res.blob();
      if (myGen !== this.gen) return;
      const url = URL.createObjectURL(blob);
      const a = new Audio(url);
      this.audio = a;
      a.playbackRate = rate();
      // Only the current generation may advance the queue, and only once —
      // otherwise a rejected play() plus a fired onerror would double-advance.
      a.onended = a.onerror = () => {
        a.onended = a.onerror = null;
        URL.revokeObjectURL(url);
        if (myGen !== this.gen) return;
        this.audio = null;
        this._next();
      };
      try {
        await a.play();
      } catch (e) {
        a.onended = a.onerror = null;
        URL.revokeObjectURL(url);
        if (myGen !== this.gen) return;
        this.audio = null;
        this._speakBrowser(text, myGen);
      }
    },

    _speakBrowser(text, gen) {
      const myGen = (gen === undefined) ? this.gen : gen;
      // stopped, or superseded by a newer utterance — stay silent
      if (!this.busy || myGen !== this.gen) return;
      if (!("speechSynthesis" in window)) { this._next(); return; }
      const u = new SpeechSynthesisUtterance(text);
      u.rate = rate();
      u.onend = u.onerror = () => {
        u.onend = u.onerror = null;
        if (myGen !== this.gen) return;
        this._next();
      };
      window.speechSynthesis.speak(u);
    },
  };

  window.AWTTS = engine;
})();
