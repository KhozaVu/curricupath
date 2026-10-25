import { useEffect } from "react";

const CANDIDATES =
  "#main-content .home-focus-grid > *, #main-content .atlas-wayfinding, #main-content .continuation-space";
const SKIP =
  ".campus-hero, .campus-hero *, [role='dialog'] *, [data-no-reveal], [data-no-reveal] *";

const supportsScrollTimeline = () =>
  typeof CSS !== "undefined" &&
  CSS.supports?.("animation-timeline: view()") === true;

/* Blocks fade and rise as they scroll into view, and reverse when scrolled back out,
   so the transition plays on every pass up or down.

   Where the browser supports scroll-driven animations the whole effect is CSS
   (animation-timeline: view(), compositor-run, scrubbed by scroll position) and this hook
   only tags the blocks. Elsewhere an IntersectionObserver toggles the same states. */
export function useScrollReveal(page, motionPreference, systemReduced) {
  useEffect(() => {
    const main = document.getElementById("main-content");
    if (!main || motionPreference === "off") return undefined;
    const native = supportsScrollTimeline();
    const io =
      !native && window.IntersectionObserver
        ? new IntersectionObserver(
            (entries) =>
              entries.forEach((entry) =>
                entry.target.setAttribute(
                  "data-reveal",
                  entry.isIntersecting ? "in" : "out",
                ),
              ),
            { rootMargin: "0px 0px -6% 0px", threshold: 0.04 },
          )
        : null;
    if (!native && !io) return undefined;

    main.setAttribute("data-reveal-mode", systemReduced ? "fade" : "rise");
    main.setAttribute("data-reveal-engine", native ? "css" : "observer");

    const tag = () => {
      const perParent = new Map();
      main.querySelectorAll(CANDIDATES).forEach((el) => {
        if (el.hasAttribute("data-reveal") || el.matches(SKIP)) return;
        // Reveal the outer block only; its children come with it.
        if (el.parentElement?.closest("[data-reveal]")) return;
        // Stagger siblings that enter together: at most the first four.
        const index = perParent.get(el.parentElement) ?? 0;
        perParent.set(el.parentElement, index + 1);
        el.style.setProperty("--reveal-i", String(Math.min(index, 3)));
        el.setAttribute("data-reveal", native ? "scrub" : "out");
        io?.observe(el);
      });
    };

    tag();
    const mo = new MutationObserver(() => tag());
    mo.observe(main, { childList: true, subtree: true });
    return () => {
      mo.disconnect();
      io?.disconnect();
      main.removeAttribute("data-reveal-mode");
      main.removeAttribute("data-reveal-engine");
      main.querySelectorAll("[data-reveal]").forEach((el) => {
        el.removeAttribute("data-reveal");
        el.style.removeProperty("--reveal-i");
      });
    };
  }, [page, motionPreference, systemReduced]);
}
