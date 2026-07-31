/* AccessWeave Sound Watch — audio-thread detector.
 *
 * This runs inside an AudioWorklet, on the browser's audio rendering thread.
 * That matters: when a tab is backgrounded, browsers pause requestAnimationFrame
 * and throttle timers to roughly once a minute, but audio processing keeps
 * running in real time. Doing the detection here is what lets Sound Watch keep
 * working while the user is in another tab or another app.
 *
 * Only decisions leave this thread — a message is posted when a sound event
 * ends. No audio is ever recorded, buffered beyond the current frame, or sent
 * anywhere.
 */
class SoundWatchProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.baseline = 0.02;
    this.calibrating = true;
    this.calibFrames = 0;
    this.sensitivity = 5;
    this.loudFrames = 0;
    this.quietFrames = 0;
    this.eventFrames = 0;
    this.burstCount = 0;
    this.framesSinceBurst = 1e9;
    this.framesSinceAlert = 1e9;
    this.meterTick = 0;

    this.port.onmessage = (e) => {
      if (e.data && typeof e.data.sensitivity === "number") {
        this.sensitivity = e.data.sensitivity;
      }
    };
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const ch = input[0];

    // RMS level of this 128-sample render quantum.
    let sum = 0;
    for (let i = 0; i < ch.length; i++) sum += ch[i] * ch[i];
    const level = Math.sqrt(sum / ch.length);

    this.framesSinceBurst++;
    this.framesSinceAlert++;

    // ~128 samples per frame; at 48kHz that's ~375 frames/second.
    const FPS = sampleRate / ch.length;

    // Learn the room's baseline for the first ~2 seconds.
    if (this.calibrating) {
      this.baseline = this.baseline * 0.9 + level * 0.1;
      if (++this.calibFrames > FPS * 2) {
        this.calibrating = false;
        this.port.postMessage({ type: "ready" });
      }
      return true;
    }

    // Report a level for the on-screen meter ~10x/second (ignored when hidden).
    if (++this.meterTick > FPS / 10) {
      this.meterTick = 0;
      this.port.postMessage({ type: "level", level });
    }

    const threshold = Math.max(0.035, this.baseline * (12 - this.sensitivity));

    if (level > threshold) {
      if (this.loudFrames === 0) {
        this.eventFrames = 0;
        if (this.framesSinceBurst < FPS * 0.9) this.burstCount++;
        else this.burstCount = 1;
      }
      this.loudFrames++;
      this.eventFrames++;
      this.quietFrames = 0;
    } else if (this.loudFrames > 0) {
      this.quietFrames++;
      this.eventFrames++;
      if (this.quietFrames > FPS * 0.12) {
        // Measure the sound itself. Counting the ~120 ms hangover made the
        // minimum-duration filter unable to ever reject anything, so every
        // click and pop was reported as a real sound.
        const durationMs = (this.loudFrames / FPS) * 1000;
        this.framesSinceBurst = 0;
        if (durationMs > 120 && this.framesSinceAlert > FPS * 3) {
          this.framesSinceAlert = 0;
          this.port.postMessage({
            type: "sound",
            durationMs,
            bursts: this.burstCount,
          });
        }
        this.loudFrames = 0;
        this.quietFrames = 0;
      }
    } else {
      // Drift the baseline slowly while it is quiet.
      this.baseline = this.baseline * 0.995 + level * 0.005;
    }
    return true;
  }
}

registerProcessor("sound-watch", SoundWatchProcessor);
