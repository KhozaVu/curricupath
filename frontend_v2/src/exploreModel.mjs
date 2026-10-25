export const TOPICS = [
  {
    id: "learning",
    title: "Machine learning",
    description: "Find patterns. Build intelligence.",
    tags: ["machine_learning", "artificial_intelligence"],
  },
  {
    id: "networks",
    title: "Networks & communication",
    description: "Connect people, systems, and ideas.",
    tags: ["networking", "telecommunications", "communications"],
  },
  {
    id: "embedded",
    title: "Electronics & embedded",
    description: "Bring software into the physical world.",
    tags: ["electronics", "embedded_systems"],
  },
];

export function courseMatchesTopic(course, topicId) {
  if (!topicId) return true;
  const topic = TOPICS.find((item) => item.id === topicId);
  if (!topic) return false;
  const tags = new Set(
    [...(course.topic_tags || []), ...(course.interest_tags || [])].map((tag) =>
      tag.toLowerCase(),
    ),
  );
  return topic.tags.some((tag) => tags.has(tag));
}

export const DEFAULT_DISCOVERY = {
  q: "",
  topic: null,
  provider: "",
  level: "",
  workload: "",
  sort: "catalogue",
  saved: false,
};

export function readDiscovery(hash) {
  const params = new URLSearchParams(hash.split("?")[1] || "");
  return {
    q: (params.get("q") || "").slice(0, 200),
    topic: TOPICS.some((topic) => topic.id === params.get("topic"))
      ? params.get("topic")
      : null,
    provider: (params.get("provider") || "").slice(0, 100),
    level: ["beginner", "intermediate", "advanced"].includes(
      params.get("level"),
    )
      ? params.get("level")
      : "",
    workload: ["light", "moderate", "heavy"].includes(params.get("workload"))
      ? params.get("workload")
      : "",
    sort: ["title", "rating"].includes(params.get("sort"))
      ? params.get("sort")
      : "catalogue",
    saved: params.get("saved") === "1",
  };
}

export function discoveryHash(hash, options) {
  const params = new URLSearchParams(hash.split("?")[1] || "");
  for (const key of Object.keys(DEFAULT_DISCOVERY)) {
    const value = options[key];
    if (value && value !== DEFAULT_DISCOVERY[key])
      params.set(key, key === "saved" ? "1" : value);
    else params.delete(key);
  }
  return `#explore${params.size ? `?${params}` : ""}`;
}

export function readCourseLink(hash) {
  const value =
    new URLSearchParams(hash.split("?")[1] || "").get("course") || "";
  return /^[A-Za-z0-9_-]{1,80}$/.test(value) ? value : null;
}

export function discoveryCourses(courses, options) {
  const query = options.q.trim().toLowerCase();
  const matches = courses.filter(
    (course) =>
      courseMatchesTopic(course, options.topic) &&
      (!options.provider || course.provider === options.provider) &&
      (!options.level || course.level === options.level) &&
      (!options.workload || course.workload === options.workload) &&
      [
        course.title,
        course.description,
        course.provider,
        ...(course.topic_tags || []),
        ...(course.interest_tags || []),
      ]
        .join(" ")
        .replaceAll("_", " ")
        .toLowerCase()
        .includes(query),
  );
  if (options.sort === "title")
    matches.sort((a, b) => a.title.localeCompare(b.title));
  if (options.sort === "rating") {
    const rating = (course) =>
      Number.isFinite(course.rating_mean) &&
      Number.isFinite(course.rating_scale) &&
      course.rating_scale > 0 &&
      course.rating_mean >= 0 &&
      course.rating_mean <= course.rating_scale
        ? course.rating_mean / course.rating_scale
        : -1;
    matches.sort(
      (a, b) =>
        rating(b) - rating(a) ||
        (Number(b.rating_count) || 0) - (Number(a.rating_count) || 0) ||
        a.title.localeCompare(b.title),
    );
  }
  return matches;
}
