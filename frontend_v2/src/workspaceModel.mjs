export const MODULE_STATES = ["completed", "current", "planned", "repeating"];
export function moduleState(profile, code) {
  return (
    MODULE_STATES.find((state) => (profile[state] || []).includes(code)) ||
    "not_taken"
  );
}
export function toggleSavedCourse(ids, id) {
  return ids.includes(id)
    ? ids.filter((value) => value !== id)
    : [...new Set([...ids, id])];
}
export function readPlanList(hash) {
  const params = new URLSearchParams(hash.split("?")[1] || "");
  return {
    query: (params.get("find") || "").slice(0, 200),
    status: [...MODULE_STATES, "not_taken"].includes(params.get("status"))
      ? params.get("status")
      : "all",
    all: params.get("all") === "1",
  };
}
export function planListHash(hash, options) {
  const params = new URLSearchParams(hash.split("?")[1] || "");
  for (const [key, value] of Object.entries({
    find: options.query,
    status: options.status === "all" ? null : options.status,
    all: options.all ? "1" : null,
  })) {
    if (value) params.set(key, value);
    else params.delete(key);
  }
  return `#plan${params.size ? `?${params}` : ""}`;
}
export function planText(profile, modules) {
  const lines = [
    `CurricuPath study plan · ${profile.programme}`,
    "Declared selections; not an official registration decision.",
    "",
  ];
  for (const state of MODULE_STATES) {
    lines.push(state[0].toUpperCase() + state.slice(1));
    const codes = profile[state] || [];
    lines.push(
      ...(codes.length
        ? codes.map((code) => {
            const item = modules.find((module) => module.course_code === code);
            return `${code} · ${item?.course_name || "Not found in this programme catalogue"}`;
          })
        : ["None selected"]),
      "",
    );
  }
  return lines.join("\n");
}
export function answerText(message) {
  const lines = [message.text || ""];
  const appendEvidence = (data) => {
    if (data.source_id)
      lines.push(`${data.source_id}${data.title ? ` · ${data.title}` : ""}`);
    for (const rule of data.rules || [])
      lines.push(
        `${rule.rule_id} · ${rule.source_id}${rule.handbook_page ? ` · Handbook page ${rule.handbook_page}` : ""}`,
        rule.plain_language || "",
      );
    for (const citation of data.citations || [])
      lines.push(
        `${citation.source_id}${citation.title ? ` · ${citation.title}` : ""}${citation.page ? ` · ${citation.page}` : ""}`,
      );
    for (const gate of data.rule_trace || [])
      if (gate.rule_ids?.length)
        lines.push(
          `${gate.gate || "Recorded check"}: ${gate.rule_ids.join(", ")}`,
        );
  };
  const data = message.data || {};
  appendEvidence(data);
  const records = [
    ...(data.recommendations || []),
    ...(data.modules || []),
    ...(data.module_matches || []),
    ...(data.module ? [data.module] : []),
  ];
  for (const record of records) {
    lines.push(
      record.course_code ||
        record.title ||
        record.course_name ||
        "Recorded result",
    );
    appendEvidence(record);
  }
  return lines.join("\n");
}
export const recordMatches = (record, query) =>
  Object.values(record)
    .filter((value) => typeof value === "string")
    .join(" ")
    .toLowerCase()
    .includes(query.trim().toLowerCase());
