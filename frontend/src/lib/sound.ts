let sharedContext: AudioContext | null = null;

function getContext(): AudioContext | null {
  if (typeof window === "undefined") return null;

  const Ctor =
    window.AudioContext ??
    (window as unknown as {
      webkitAudioContext?: typeof AudioContext;
    }).webkitAudioContext;

  if (!Ctor) return null;

  if (!sharedContext) sharedContext = new Ctor();

  return sharedContext;
}

function playNote(
  ctx: AudioContext,
  freq: number,
  start: number,
  duration: number,
) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = "sine";
  osc.frequency.value = freq;

  gain.gain.setValueAtTime(0, start);
  gain.gain.linearRampToValueAtTime(0.18, start + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(start);
  osc.stop(start + duration + 0.02);
}

function playFallbackChime() {
  if (typeof window === "undefined") return;

  const audio = new Audio("/sounds/chime.wav");
  audio.volume = 0.8;

  audio.play().catch(() => {
    // Browser blocked audio playback.
  });
}

/** The chime played when a search/identify successfully matches a verse. */
export async function playVerseFoundChime() {
  const ctx = getContext();

  // Web Audio isn't available → use WAV fallback.
  if (!ctx) {
    playFallbackChime();
    return;
  }

  // Make sure the context is running before scheduling audio.
  if (ctx.state === "suspended") {
    try {
      await ctx.resume();
    } catch {
      playFallbackChime();
      return;
    }
  }

  // If the context still isn't usable, use the fallback.
  if (ctx.state !== "running") {
    playFallbackChime();
    return;
  }

  const now = ctx.currentTime;

  playNote(ctx, 659.25, now, 0.14); // E5
  playNote(ctx, 987.77, now + 0.09, 0.22); // B5
}