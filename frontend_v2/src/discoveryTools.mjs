export function cleanCourseIds(value, limit = 6) {
  return [...new Set((Array.isArray(value) ? value : []).filter(id => typeof id === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(id)))].slice(0, limit);
}
export function toggleComparison(value, id) {
  const ids = cleanCourseIds(value, 3);
  if (!cleanCourseIds([id]).length) return ids;
  return ids.includes(id) ? ids.filter(item => item !== id) : ids.length < 3 ? [...ids, id] : ids;
}
export function rememberCourse(value, id) {
  if (!cleanCourseIds([id]).length) return cleanCourseIds(value);
  return cleanCourseIds([id, ...cleanCourseIds(value).filter(item => item !== id)]);
}
export function discoveryPick(courses, previousId, random = Math.random) {
  const pool = courses.filter(course => course.course_id !== previousId);
  const choices = pool.length ? pool : courses;
  return choices.length ? choices[Math.min(choices.length - 1, Math.max(0, Math.floor(random() * choices.length)))] : null;
}
export const COMPARISON_FIELDS = [
  ["Provider", course => course.provider || "Not recorded"],
  ["Level", course => course.level || "Not recorded"],
  ["Workload", course => course.workload || "Not recorded"],
  ["Format", course => course.format || "Not recorded"],
  ["Learner rating", course => course.rating_mean ? `${course.rating_mean}/${course.rating_scale || 5}` : "Not recorded"],
  ["Rating count", course => course.rating_count != null ? Number(course.rating_count).toLocaleString() : "Not recorded"],
  ["Focus", course => (course.topic_tags || []).map(tag => tag.replaceAll("_", " ")).join(" · ") || "Not recorded"],
];
