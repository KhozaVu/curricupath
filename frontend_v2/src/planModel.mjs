export const selectedCodes = (profile) =>
  new Set(
    ["completed", "current", "planned", "repeating"].flatMap(
      (key) => profile[key] || [],
    ),
  );

export function nextAction(profile, ready) {
  if (!ready)
    return {
      title: "Your path starts here.",
      text: "Choose your degree and add your module history to make guidance personal.",
      label: "Set up your degree profile",
      destination: "profile",
    };
  if (!profile.historyConfirmed)
    return {
      title: "Start with what you know.",
      text: "Confirm your completed and current modules so the advisor can check the right history.",
      label: "Review your module history",
      destination: "profile",
    };
  if (profile.repeating?.length)
    return {
      title: "Make space for a fresh start.",
      text: `${profile.repeating.length} module${profile.repeating.length === 1 ? " is" : "s are"} marked for repeat. Review your timeline before adding more.`,
      label: "Review your study timeline",
      destination: "plan",
      tab: "timeline",
    };
  if (profile.planned?.length)
    return {
      title: "See what comes before.",
      text: `You have ${profile.planned.length} planned module${profile.planned.length === 1 ? "" : "s"}. Open the first one to review its recorded requirements.`,
      label: `Review ${profile.planned[0]}`,
      destination: "plan",
      module: profile.planned[0],
    };
  return {
    title: "Find your next connection.",
    text: "Explore the programme’s modules and recorded dependencies, then add a module to your study plan.",
    label: "Explore your curriculum",
    destination: "plan",
  };
}

export function graphForMode(graph, profile, mode, selected, highlight = []) {
  if (mode === "dependencies") return graph;
  const keep = selectedCodes(profile);
  for (const code of [selected, ...highlight].filter(Boolean)) keep.add(code);
  // Include the recorded requirements of selected modules, without inferring eligibility.
  let grew = true;
  while (grew) {
    grew = false;
    for (const edge of graph.edges) {
      if (keep.has(edge.to) && !keep.has(edge.from)) {
        keep.add(edge.from);
        grew = true;
      }
    }
  }
  return {
    ...graph,
    nodes: graph.nodes.filter((node) => keep.has(node.course_code)),
    edges: graph.edges.filter(
      (edge) => keep.has(edge.from) && keep.has(edge.to),
    ),
  };
}

export function dependencyClosure(graph, seeds) {
  const keep = new Set(seeds.filter(Boolean));
  let grew = true;
  while (grew) {
    grew = false;
    for (const edge of graph.edges) {
      if (keep.has(edge.to) && !keep.has(edge.from)) {
        keep.add(edge.from);
        grew = true;
      }
    }
  }
  return keep;
}

export function graphForView(
  graph,
  profile,
  mode,
  selected,
  highlight = [],
  year = null,
  focus = false,
) {
  const base = graphForMode(graph, profile, mode, selected, highlight);
  const seeds = selected ? [selected] : highlight;
  let keep;
  if (focus && seeds.length) keep = dependencyClosure(graph, seeds);
  else if (year)
    keep = dependencyClosure(
      graph,
      base.nodes
        .filter((node) => Number(node.year_of_study) === Number(year))
        .map((node) => node.course_code),
    );
  else return base;
  return {
    ...graph,
    nodes: graph.nodes.filter((node) => keep.has(node.course_code)),
    edges: graph.edges.filter(
      (edge) => keep.has(edge.from) && keep.has(edge.to),
    ),
  };
}

export function readPlanOptions(hash) {
  const params = new URLSearchParams(hash.split("?")[1] || "");
  const year = Number(params.get("year"));
  return {
    mode: ["study", "dependencies"].includes(params.get("mode"))
      ? params.get("mode")
      : null,
    year: Number.isInteger(year) && year >= 1 && year <= 6 ? year : null,
    focus: params.get("focus") === "chain",
  };
}

export function planOptionsHash(hash, options) {
  const params = new URLSearchParams(hash.split("?")[1] || "");
  for (const [key, value] of Object.entries({
    mode: options.mode,
    year: options.year,
    focus: options.focus ? "chain" : null,
  })) {
    if (value) params.set(key, value);
    else params.delete(key);
  }
  return `#plan${params.size ? `?${params}` : ""}`;
}

export function readRoute(hash) {
  const [key, search = ""] = hash.replace(/^#/, "").split("?");
  const params = new URLSearchParams(search);
  const aliases = {
    journey: "plan",
    library: "explore",
    careers: "explore",
    achievements: "home",
    profile: "home",
    evidence: "home",
  };
  return {
    page:
      aliases[key] ||
      (["home", "plan", "advisor", "explore"].includes(key) ? key : "home"),
    planTab:
      params.get("tab") === "timeline" || key === "journey"
        ? "timeline"
        : "map",
    exploreTab:
      params.get("tab") === "careers" || key === "careers"
        ? "careers"
        : "courses",
    module: /^[A-Z]{3,5}\d{3,5}[A-Z]?$/.test(params.get("module") || "")
      ? params.get("module")
      : null,
    drawer: ["profile", "evidence"].includes(key) ? key : null,
  };
}

export function recommendationReason(item) {
  if (item.reasons?.length) return item.reasons[0];
  if (item.matched_tags?.length)
    return `Matches your stated interests: ${item.matched_tags.map((tag) => tag.replaceAll("_", " ")).join(", ")}.`;
  const parts = item.score_components || {};
  const signals = [];
  if (parts.interest > 0) signals.push("stated interests");
  if (parts.career > 0) signals.push("career goals");
  if (parts.workload_format > 0) signals.push("workload or format preferences");
  if (signals.length)
    return `Ranked using overlap with your ${signals.join(" and ")}.`;
  if (parts.text > 0 || parts.semantic > 0)
    return "Ranked using relevance to your question.";
  return (
    item.description ||
    "No personal ranking explanation was supplied for this result."
  );
}

export function moduleConnections(graph, code) {
  if (!graph || !code) return [];
  return graph.edges
    .filter((edge) => edge.to === code || edge.from === code)
    .map((edge) => {
      const incoming = edge.to === code;
      const other = incoming ? edge.from : edge.to;
      return {
        ...edge,
        incoming,
        code: other,
        name:
          graph.nodes.find((node) => node.course_code === other)?.course_name ||
          "Recorded curriculum reference",
      };
    });
}
