import { DEFAULT_DISCOVERY, discoveryHash } from "./exploreModel.mjs";
const DESTINATIONS = new Set(["home", "plan", "advisor", "explore"]);

export function rememberView(hash, views) {
  const page = hash.replace(/^#/, "").split("?")[0];
  if (!DESTINATIONS.has(page)) return views;
  if (page === "home" || page === "advisor") return { ...views, [page]: `#${page}` };
  const params = new URLSearchParams(hash.split("?")[1] || "");
  if (page === "explore") params.delete("course");
  return { ...views, [page]: `#${page}${params.size ? `?${params}` : ""}` };
}

export function destinationHash(destination, views, options = {}) {
  if (!DESTINATIONS.has(destination)) return "#home";
  const hasDiscovery = destination === "explore" && Object.keys(DEFAULT_DISCOVERY).some((key) => Object.hasOwn(options, key));
  if (!options.tab && !options.module && !hasDiscovery) return views[destination] || `#${destination}`;
  const params = new URLSearchParams();
  if (options.tab) params.set("tab", options.tab);
  if (options.module) params.set("module", options.module);
  if (hasDiscovery) return discoveryHash(`#explore${params.size ? `?${params}` : ""}`, { ...DEFAULT_DISCOVERY, ...options });
  return `#${destination}?${params}`;
}
