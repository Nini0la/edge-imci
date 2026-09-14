import { afterEach, describe, expect, it, vi } from "vitest";
import { createAudioCapture, maxAudioBytes } from "./audio";

class Recorder {
  static instances: Recorder[] = [];
  static isTypeSupported = (type: string) => type === "audio/webm;codecs=opus";
  mimeType = "audio/webm;codecs=opus";
  state = "inactive";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() { Recorder.instances.push(this); }
  start() { this.state = "recording"; }
  stop() { this.state = "inactive"; }
}

function setup(getUserMedia?: () => Promise<unknown>) {
  const track = { stop: vi.fn() };
  const stream = { getTracks: () => [track] };
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: getUserMedia ?? vi.fn().mockResolvedValue(stream) } });
  vi.stubGlobal("MediaRecorder", Recorder);
  const callbacks = { state: vi.fn(), audio: vi.fn(), error: vi.fn() };
  return { capture: createAudioCapture(callbacks), callbacks, stream, track };
}

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); Recorder.instances = []; });

describe("ephemeral audio capture", () => {
  it("stops a late microphone grant after cancel without creating a recorder", async () => {
    let grant!: (stream: unknown) => void;
    const pending = new Promise((resolve) => { grant = resolve; });
    const { capture, stream, track, callbacks } = setup(() => pending);
    const recording = capture.record();
    capture.cancel();
    grant(stream);
    await recording;
    expect(track.stop).toHaveBeenCalledOnce();
    expect(Recorder.instances).toHaveLength(0);
    expect(callbacks.audio).not.toHaveBeenCalled();
  });

  it("times out permission and rejects the later grant", async () => {
    vi.useFakeTimers();
    let grant!: (stream: unknown) => void;
    const pending = new Promise((resolve) => { grant = resolve; });
    const { capture, callbacks, stream, track } = setup(() => pending);
    const recording = capture.record();
    vi.advanceTimersByTime(30_000);
    expect(callbacks.error).toHaveBeenCalledWith(expect.stringContaining("permission timed out"));
    grant(stream);
    await recording;
    expect(track.stop).toHaveBeenCalledOnce();
    expect(Recorder.instances).toHaveLength(0);
  });

  it("automatically stops at 60 seconds and releases tracks before playback", async () => {
    vi.useFakeTimers();
    const { capture, callbacks, track } = setup();
    await capture.record();
    const recorder = Recorder.instances[0];
    recorder.ondataavailable?.({ data: new Blob(["recorded"]) });
    vi.advanceTimersByTime(60_000);
    expect(recorder.state).toBe("inactive");
    expect(track.stop).toHaveBeenCalledOnce();
    recorder.onstop?.();
    expect(callbacks.audio).toHaveBeenCalledWith(expect.objectContaining({ type: "audio/webm;codecs=opus", size: 8 }));
    expect(recorder.ondataavailable).toBeNull();
  });

  it("discards oversized audio instead of submitting a truncated report", async () => {
    const { capture, callbacks, track } = setup();
    await capture.record();
    Recorder.instances[0].ondataavailable?.({ data: new Blob([new Uint8Array(maxAudioBytes + 1)]) });
    expect(callbacks.error).toHaveBeenCalledWith(expect.stringContaining("exceeded 5 MB"));
    expect(callbacks.audio).not.toHaveBeenCalled();
    expect(track.stop).toHaveBeenCalledOnce();
  });

  it("ignores queued audio and errors from cancelled recordings", async () => {
    const { capture, callbacks, track } = setup();
    await capture.record();
    const old = Recorder.instances[0];
    const queuedData = old.ondataavailable;
    const queuedStop = old.onstop;
    const queuedError = old.onerror;
    capture.cancel();
    await capture.record();
    queuedData?.({ data: new Blob(["stale"]) });
    queuedStop?.();
    queuedError?.();
    expect(callbacks.audio).not.toHaveBeenCalled();
    expect(callbacks.error).not.toHaveBeenCalled();
    expect(Recorder.instances[1].state).toBe("recording");
    capture.cancel();
    expect(track.stop).toHaveBeenCalledTimes(2);
  });

  it("reports permission failures without leaving recording active", async () => {
    const { capture, callbacks } = setup(() => Promise.reject(new Error("permission denied")));
    await capture.record();
    expect(callbacks.state).toHaveBeenLastCalledWith("idle");
    expect(callbacks.error).toHaveBeenCalledWith(expect.stringContaining("type findings"));
  });
});
