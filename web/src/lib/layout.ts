import { useSyncExternalStore } from "react";

export const mobileQuery = "(max-width: 900px)";

export function resolveLayout(search: string, narrow: boolean): "mobile" | "desktop" {
  const requested = new URLSearchParams(search).get("layout");
  return requested === "mobile" || requested === "desktop" ? requested : narrow ? "mobile" : "desktop";
}

function subscribe(notify: () => void) {
  const media = window.matchMedia(mobileQuery);
  media.addEventListener("change", notify);
  window.addEventListener("popstate", notify);
  return () => {
    media.removeEventListener("change", notify);
    window.removeEventListener("popstate", notify);
  };
}

export function useMobileLayout() {
  return useSyncExternalStore(subscribe, () =>
    resolveLayout(window.location.search, window.matchMedia(mobileQuery).matches) === "mobile", () => false);
}
