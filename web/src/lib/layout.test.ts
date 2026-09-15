import { useSyncExternalStore } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mobileQuery, resolveLayout, useMobileLayout } from "./layout";

vi.mock("react", () => ({ useSyncExternalStore: vi.fn() }));
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); });

describe("presentation selection", () => {
  it("selects the phone layout for narrow viewports", () => {
    expect(resolveLayout("", true)).toBe("mobile");
    expect(resolveLayout("", false)).toBe("desktop");
  });
  it("supports explicit preview modes without changing clinical configuration", () => {
    expect(resolveLayout("?layout=mobile", false)).toBe("mobile");
    expect(resolveLayout("?layout=desktop", true)).toBe("desktop");
    expect(resolveLayout("?layout=unknown", true)).toBe("mobile");
  });

  it("subscribes to the inclusive 900px media query and history changes, reads fresh snapshots, and cleans up", () => {
    const media = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() };
    const location = { search: "" };
    vi.stubGlobal("window", { matchMedia: vi.fn().mockReturnValue(media), location,
      addEventListener: vi.fn(), removeEventListener: vi.fn() });
    vi.mocked(useSyncExternalStore).mockReturnValue(true);
    expect(useMobileLayout()).toBe(true);
    expect(useSyncExternalStore).toHaveBeenCalledOnce();
    const [subscribe, getSnapshot, getServerSnapshot] = vi.mocked(useSyncExternalStore).mock.calls[0];
    const notify = vi.fn();
    const cleanup = subscribe(notify);
    expect(mobileQuery).toBe("(max-width: 900px)");
    expect(window.matchMedia).toHaveBeenCalledWith(mobileQuery);
    expect(media.addEventListener).toHaveBeenCalledWith("change", notify);
    expect(window.addEventListener).toHaveBeenCalledWith("popstate", notify);
    expect(getSnapshot()).toBe(false);
    media.matches = true;
    media.addEventListener.mock.calls[0][1]();
    expect(notify).toHaveBeenCalledTimes(1);
    expect(getSnapshot()).toBe(true);
    location.search = "?layout=desktop";
    const popstate = vi.mocked(window.addEventListener).mock.calls[0][1] as () => void;
    popstate();
    expect(notify).toHaveBeenCalledTimes(2);
    expect(getSnapshot()).toBe(false);
    location.search = "?layout=mobile";
    media.matches = false;
    expect(getSnapshot()).toBe(true);
    location.search = "?layout=unknown";
    expect(getSnapshot()).toBe(false);
    expect(getServerSnapshot?.()).toBe(false);
    cleanup();
    expect(media.removeEventListener).toHaveBeenCalledExactlyOnceWith("change", notify);
    expect(window.removeEventListener).toHaveBeenCalledExactlyOnceWith("popstate", notify);
  });
});
