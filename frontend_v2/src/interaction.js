import { useCallback, useEffect, useRef, useState } from "react";

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);
  return matches;
}

// Keep focus in place while the exit animation runs, then restore the opener.
export function useOverlayClose(onClose, ref) {
  const callback = useRef(onClose);
  callback.current = onClose;
  const timer = useRef(null);
  const [closing, setClosing] = useState(false);
  useEffect(() => () => clearTimeout(timer.current), []);
  const close = useCallback(() => {
    if (timer.current !== null) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      ref.current?.closest('[data-motion="reduced"]');
    if (reduced) callback.current();
    else {
      setClosing(true);
      timer.current = setTimeout(() => callback.current(), 180);
    }
  }, [ref]);
  return { closing, close };
}

export function useDialogFocus(ref, onClose, { modal = true, enabled = true } = {}) {
  const callback = useRef(onClose);
  const lastFocus = useRef(null);
  callback.current = onClose;
  useEffect(() => {
    if (!enabled) return;
    const previous = document.activeElement;
    const node = ref.current;
    const focusTarget = lastFocus.current?.isConnected ? lastFocus.current : node.querySelector("button");
    focusTarget?.focus({ preventScroll: true });
    const remember = (event) => { lastFocus.current = event.target; };
    const key = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        callback.current();
      }
      if (!modal || event.key !== "Tab") return;
      const items = [...node.querySelectorAll(
        'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex="0"]',
      )].filter(el => el.tabIndex >= 0 && el.getClientRects().length && !el.closest("[inert]"));
      const first = items[0], last = items.at(-1);
      if (!node.contains(document.activeElement) || (!event.shiftKey && document.activeElement === last)) {
        event.preventDefault(); first?.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last?.focus();
      }
    };
    const overflow = document.body.style.overflow;
    if (modal) document.body.style.overflow = "hidden";
    const outsideKey = (event) => {
      if (event.key === "Escape" && !node.contains(event.target) && !document.querySelector(".drawer-backdrop")) {
        event.preventDefault();
        callback.current();
      }
    };
    node.addEventListener("keydown", key);
    node.addEventListener("focusin", remember);
    if (!modal) window.addEventListener("keydown", outsideKey);
    return () => {
      node.removeEventListener("keydown", key);
      node.removeEventListener("focusin", remember);
      if (!modal) window.removeEventListener("keydown", outsideKey);
      if (modal) document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus({ preventScroll: true });
      else document.querySelector('main:not([inert])')?.focus({ preventScroll: true });
    };
  }, [ref, modal, enabled]);
}
