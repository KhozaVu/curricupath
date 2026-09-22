const state = { profiles: [], courses: [], grades: {}, slot: null, judgeId: "" };
const byId = id => document.getElementById(id);

function make(tag, className = "", text = "") {
  const item = document.createElement(tag);
  item.className = className;
  item.textContent = text;
  return item;
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function toast(message) {
  byId("toast").textContent = message;
  byId("toast").classList.add("visible");
  setTimeout(() => byId("toast").classList.remove("visible"), 2400);
}

function readinessText(value, prototype) {
  const human = `${value.profiles} profiles x ${value.courses} courses | Human track: ${value.judge_1_completed}/${value.expected_judgements_per_judge} + ${value.judge_2_completed}/${value.expected_judgements_per_judge}`;
  if (!prototype) return `${human} | Training ready: ${value.training_ready ? "yes" : "no"}`;
  return `${human} | Prototype labels: ${prototype.labels}/${prototype.expected_labels} | Prototype model: ${prototype.model_trained ? "ready" : "not trained"}`;
}

async function loadSetup() {
  const data = await request("/api/setup");
  state.profiles = data.profiles;
  state.courses = data.courses;
  byId("readiness").textContent = readinessText(data.readiness, data.prototype);
  byId("profile-status").textContent = data.readiness.profiles_approved ? "Approved" : "Draft review required";
  byId("approve-profiles").disabled = data.readiness.profiles_approved;
  byId("profile-preview").replaceChildren(...state.profiles.map(profile => {
    const item = document.createElement("article");
    item.className = "mini-profile";
    item.append(make("b", "", `${profile.profile_id} | ${profile.split}`), make("span", "", profile.query));
    return item;
  }));
  byId("profile-select").replaceChildren(...state.profiles.map(profile => {
    const option = document.createElement("option");
    option.value = profile.profile_id;
    option.textContent = `${profile.profile_id} | ${profile.query}`;
    return option;
  }));
  if (data.readiness.profiles_approved) byId("review-panel").classList.add("approved");
  updateAdjudicationStatus(data.readiness);
}

byId("approve-profiles").addEventListener("click", async () => {
  if (!byId("review-confirmation").checked) return toast("Confirm that every profile was reviewed.");
  try {
    const readiness = await request("/api/profiles/approve", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({reviewer: byId("reviewer").value}),
    });
    byId("readiness").textContent = readinessText(readiness);
    toast("Profile set approved and frozen.");
    await loadSetup();
  } catch (error) { toast(error.message); }
});

byId("start-judging").addEventListener("click", async () => {
  state.slot = Number(byId("judge-slot").value);
  state.judgeId = byId("judge-id").value.trim();
  try {
    const judge = await request(`/api/judge?slot=${state.slot}&judge_id=${encodeURIComponent(state.judgeId)}`);
    state.grades = judge.grades;
    updateJudgeProgress(judge);
    byId("workspace").classList.remove("hidden");
    renderProfile();
  } catch (error) { toast(error.message); }
});

byId("profile-select").addEventListener("change", renderProfile);
byId("next-incomplete").addEventListener("click", () => {
  const profile = state.profiles.find(candidate => state.courses.some(course => state.grades[`${candidate.profile_id}|${course.course_id}`] == null));
  if (!profile) return toast("Every item in this judge file is complete.");
  byId("profile-select").value = profile.profile_id;
  renderProfile();
});

function renderProfile() {
  const profile = state.profiles.find(item => item.profile_id === byId("profile-select").value);
  if (!profile) return;
  byId("active-profile").replaceChildren(
    make("h3", "", profile.query),
    make("small", "", `Interests: ${profile.interests.join(", ") || "none"} | Careers: ${profile.career_preferences.join(", ") || "none"} | Workload: ${profile.workload_preference || "unspecified"}`),
  );
  byId("course-list").replaceChildren(...state.courses.map(course => courseRow(profile, course)));
}

function courseRow(profile, course) {
  const row = document.createElement("article");
  row.className = "course-row";
  const copy = document.createElement("div");
  copy.append(
    make("h3", "", `${course.course_id} | ${course.title}`),
    make("p", "", `${course.description} ${course.provider} | ${course.level} | ${course.workload}`),
  );
  const buttons = document.createElement("div");
  buttons.className = "grade-buttons";
  const key = `${profile.profile_id}|${course.course_id}`;
  [0, 1, 2, 3].forEach(grade => {
    const button = document.createElement("button");
    button.textContent = grade;
    button.title = ["Irrelevant or conflicting", "Weak or secondary", "Relevant and useful", "Excellent recommendation"][grade];
    button.classList.toggle("selected", state.grades[key] === grade);
    button.addEventListener("click", () => saveGrade(profile.profile_id, course.course_id, grade));
    buttons.append(button);
  });
  row.append(copy, buttons);
  return row;
}

async function saveGrade(profileId, courseId, grade) {
  try {
    const judge = await request("/api/judge/grade", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({slot: state.slot, judge_id: state.judgeId, profile_id: profileId, course_id: courseId, grade}),
    });
    state.grades = judge.grades;
    updateJudgeProgress(judge);
    renderProfile();
  } catch (error) { toast(error.message); }
}

function updateJudgeProgress(judge) {
  byId("judge-progress").textContent = `${judge.completed} / ${judge.total}`;
}

byId("prepare-adjudication").addEventListener("click", async () => {
  try {
    const readiness = await request("/api/adjudication/prepare", {method: "POST"});
    byId("readiness").textContent = readinessText(readiness);
    await loadDisagreements();
  } catch (error) { toast(error.message); }
});

async function loadDisagreements() {
  const data = await request("/api/adjudication");
  updateAdjudicationStatus(data.readiness);
  const unresolved = data.disagreements.filter(item => item.final_grade == null);
  byId("disagreement-list").replaceChildren(...unresolved.map(disagreementRow));
  if (!unresolved.length) toast("Adjudication is complete. The training data is ready.");
}

function disagreementRow(item) {
  const profile = state.profiles.find(value => value.profile_id === item.profile_id);
  const course = state.courses.find(value => value.course_id === item.course_id);
  const row = document.createElement("article");
  row.className = "disagreement";
  const copy = document.createElement("div");
  copy.append(
    make("b", "", `${item.profile_id}: ${profile.query}`),
    make("p", "", `${item.course_id}: ${course.title}`),
    make("p", "", `Judge 1: ${item.judge_1_grade} | Judge 2: ${item.judge_2_grade}`),
  );
  const controls = document.createElement("div");
  const notes = document.createElement("input");
  notes.placeholder = "Reason for final grade";
  const grades = document.createElement("div");
  grades.className = "grade-buttons";
  for (let grade = Math.min(item.judge_1_grade, item.judge_2_grade); grade <= Math.max(item.judge_1_grade, item.judge_2_grade); grade += 1) {
    const button = document.createElement("button");
    button.textContent = grade;
    button.addEventListener("click", async () => {
      try {
        await request("/api/adjudication", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({profile_id: item.profile_id, course_id: item.course_id, final_grade: grade, notes: notes.value})});
        await loadDisagreements();
      } catch (error) { toast(error.message); }
    });
    grades.append(button);
  }
  controls.append(notes, grades);
  row.append(copy, controls);
  return row;
}

function updateAdjudicationStatus(readiness) {
  byId("adjudication-progress").textContent = readiness.training_ready
    ? "Training ready"
    : readiness.adjudication_prepared
      ? `${readiness.unresolved_adjudications} unresolved`
      : "Waiting for completed judge files";
}

loadSetup().catch(error => toast(error.message));
