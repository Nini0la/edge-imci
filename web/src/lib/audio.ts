import { createRequestGate } from "./assessment";

export const maxAudioBytes = 5_000_000;
export const audioMimeTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus", "audio/ogg", "audio/wav"];
export type AudioState = "idle" | "permission" | "recording" | "stopping";

export function createAudioCapture(callbacks: {
  state: (state: AudioState) => void;
  audio: (blob: Blob) => void;
  error: (message: string) => void;
}) {
  const gate = createRequestGate();
  let recorder: MediaRecorder | undefined;
  let stream: MediaStream | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const stopTracks = () => { stream?.getTracks().forEach((track) => track.stop()); stream = undefined; };
  const cleanup = () => {
    clearTimeout(timer);
    if (recorder) {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      recorder.onerror = null;
      try { if (recorder.state !== "inactive") recorder.stop(); }
      catch { /* Tracks must still be released if the device has disconnected. */ }
      recorder = undefined;
    }
    stopTracks();
  };
  const cancel = () => { gate.cancel(); cleanup(); callbacks.state("idle"); };
  const fail = (message: string) => { cancel(); callbacks.error(message); };
  const stop = () => {
    clearTimeout(timer);
    if (recorder?.state === "recording") {
      callbacks.state("stopping");
      try { recorder.stop(); }
      catch { fail("Recording could not be stopped safely and was discarded. Please type findings or retry."); }
      finally { stopTracks(); }
    }
  };
  return {
    cancel,
    stop,
    async record() {
      cancel();
      const request = gate.begin();
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
        fail("Audio recording is unavailable in this browser. Use the section text field instead.");
        return;
      }
      const mimeType = audioMimeTypes.find((type) => MediaRecorder.isTypeSupported(type));
      if (!mimeType) { fail("No supported audio format. Use the section text field instead."); return; }
      callbacks.state("permission");
      timer = setTimeout(() => {
        if (request.isCurrent()) fail("Microphone permission timed out. You can retry or type findings.");
      }, 30_000);
      try {
        const granted = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!request.isCurrent()) {
          granted.getTracks().forEach((track) => track.stop());
          return;
        }
        clearTimeout(timer);
        stream = granted;
        recorder = new MediaRecorder(stream, { mimeType });
        const actualType = recorder.mimeType || mimeType;
        const chunks: Blob[] = [];
        let bytes = 0;
        recorder.ondataavailable = (event) => {
          if (!request.isCurrent()) return;
          bytes += event.data.size;
          if (bytes > maxAudioBytes) { fail("Recording exceeded 5 MB and was discarded. Record a shorter report or type findings."); return; }
          if (event.data.size) chunks.push(event.data);
          if (bytes === maxAudioBytes) stop();
        };
        recorder.onerror = () => {
          if (request.isCurrent()) fail("Microphone recording failed. Please retry or type findings.");
        };
        recorder.onstop = () => {
          if (!request.isCurrent()) return;
          const blob = new Blob(chunks, { type: actualType });
          cleanup();
          callbacks.state("idle");
          if (blob.size) callbacks.audio(blob);
          else callbacks.error("No audio was recorded. Please retry or type findings.");
        };
        recorder.start(250);
        callbacks.state("recording");
        timer = setTimeout(() => { if (request.isCurrent()) stop(); }, 60_000);
      } catch {
        if (request.isCurrent()) fail("Microphone access failed. Check permission and your microphone, or type findings below.");
      }
    },
  };
}
