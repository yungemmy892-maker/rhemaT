import { useCallback, useEffect, useRef, useState } from "react";

// The Web Speech API's SpeechRecognition interface isn't in TypeScript's
// default DOM lib, and Safari/older browsers only expose the prefixed
// webkitSpeechRecognition — these declarations + the runtime lookup below
// handle both.
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  [index: number]: { transcript: string };
}
interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

export type VoiceRecognitionStatus = "idle" | "listening" | "error" | "unsupported";

interface UseVoiceRecognitionOptions {
  /** Called once speech has paused and a final transcript is available. */
  onFinalResult: (transcript: string) => void;
  lang?: string;
}

export function useVoiceRecognition({ onFinalResult, lang = "en-US" }: UseVoiceRecognitionOptions) {
  const [status, setStatus] = useState<VoiceRecognitionStatus>("idle");
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const finalizedRef = useRef(false);

  useEffect(() => {
    const SpeechRecognitionCtor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setStatus("unsupported");
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = lang;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      let combined = "";
      let isFinal = false;
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        combined += result[0].transcript;
        if (result.isFinal) isFinal = true;
      }
      setTranscript(combined);
      if (isFinal && !finalizedRef.current) {
        finalizedRef.current = true;
        onFinalResult(combined.trim());
      }
    };

    recognition.onerror = () => {
      setStatus("error");
    };

    recognition.onend = () => {
      // If speech ended without ever producing a final result (e.g. the
      // person stayed silent), fall back to whatever interim transcript we
      // have so the flow doesn't hang forever on "Listening…".
      if (!finalizedRef.current && transcript.trim()) {
        finalizedRef.current = true;
        onFinalResult(transcript.trim());
      }
    };

    recognitionRef.current = recognition;
    setStatus("listening");
    finalizedRef.current = false;
    try {
      recognition.start();
    } catch {
      setStatus("error");
    }

    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      try {
        recognition.stop();
      } catch {
        // already stopped — fine.
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return { status, transcript, stop };
}
