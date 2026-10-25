"""Diagnostic: how does CurricuPath behave as a module question becomes more ambiguous?

Not part of the frozen evaluation protocol. The prompts, targets and cooperative replies are
developer-generated so that the clarification mechanism can be exercised systematically; results
describe mechanism behaviour, not validated accuracy. No frozen case file is read or modified.

Each target module is asked about at five ambiguity levels in four phrasings. Every prompt runs
twice: once as a clarification off, and once where a clarification question (if asked) receives one
cooperative reply giving the module's full name, as a student choosing from the offered options would.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
OUTPUT = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5" / "results" / "diagnostics" / "clarification_sweep"

from app.evaluation.intent_scoring import wilson_interval

# code, programme, shortened or family name (level 2), single topic word (level 3)
DEVELOPMENT_TARGETS = [
    ("ELEN3012A", "EFA03", "Signals and Systems", "signals"),
    ("ELEN2005A", "EFA03", "Signals and Systems", "signals"),
    ("ELEN3009A", "EFA03", "Software Development", "software"),
    ("ELEN2020A", "EFA03", "Software Development", "software"),
    ("MATH1049A", "EFA03", "Engineering Mathematics", "mathematics"),
    ("ELEN3016A", "EFA03", "Control", "control"),
    ("ELEN3002A", "EFA03", "Electronics", "electronics"),
    ("ELEN2016A", "EFA03", "Electronics", "electronics"),
    ("ELEN4018A", "EFA03", "Power", "power"),
    ("ELEN3017A", "EFA03", "Engineering Design", "design"),
]
LEVELS = [
    (0, "Exact module code"),
    (1, "Full module name"),
    (2, "Name without series (I, II, A, B)"),
    (3, "Single topic word"),
    (4, "No topic at all"),
]
DEVELOPMENT_FRAMES = ["{x}", "Tell me about {x}", "Who teaches {x}?", "What is {x} about?"]

# Held out: module families and phrasings not looked at while the fixes were written.
HELDOUT_TARGETS = [
    ("PHYS1033A", "EFA03", "Engineering Physics", "physics"),
    ("PHYS1032A", "EFA03", "Engineering Physics", "physics"),
    ("FEBE1004A", "EFA03", "Engineering Analysis and Design", "analysis"),
    ("AFRL1005A", "EFA03", "Language and Culture", "language"),
    ("COMS2004A", "EFA04", "Data Structures", "data"),
    ("ELEN4022A", "EFA04", "Quantum Computing", "computing"),
]
HELDOUT_FRAMES = ["Can you give me info on {x}", "I need details on {x}", "{x} please", "Which lecturer runs {x}?"]
SETS = {"development": (DEVELOPMENT_TARGETS, DEVELOPMENT_FRAMES), "heldout": (HELDOUT_TARGETS, HELDOUT_FRAMES)}
TARGETS, FRAMES = SETS["development"]
OUTCOMES = ["answered_correct", "answered_wrong", "asked_with_options", "asked_generic", "refused", "other"]


def _reference(level: int, code: str, name: str, family: str, topic: str) -> str:
    return {0: code, 1: name, 2: family, 3: topic, 4: "that module"}[level]


def classify(response: dict, target: str) -> str:
    status = response.get("status")
    if status == "ok":
        module = (response.get("module") or {}).get("course_code")
        return "answered_correct" if module == target else "answered_wrong"
    if status in {"clarification_required", "needs_clarification"}:
        return "asked_with_options" if response.get("module_matches") else "asked_generic"
    if status == "out_of_scope":
        return "refused"
    return "other"


def correct(response: dict, target: str) -> bool:
    return response.get("status") == "ok" and (response.get("module") or {}).get("course_code") == target


def run(client, names, reply_style="name"):
    rows = []
    for code, programme, family, topic in TARGETS:
        name = names[code]
        for level, _ in LEVELS:
            for frame in FRAMES:
                prompt = frame.format(x=_reference(level, code, name, family, topic))
                payload = {"message": prompt, "programme_code": programme}
                first = client.post("/advisor", json=payload).json()
                outcome = classify(first, code)
                final = first
                replied = False
                if outcome.startswith("asked"):
                    final = client.post("/advisor", json={"message": name if reply_style == "name" else code,
                                                          "programme_code": programme,
                                                          "session_id": first.get("session_id")}).json()
                    replied = True
                ablation = client.post("/advisor", json={**payload, "allow_clarification": False}).json()
                options = [m["course_code"] for m in (first.get("module_matches") or [])]
                rows.append({
                    "target": code, "target_name": name, "level": level, "frame": frame, "prompt": prompt,
                    "first_status": first.get("status"), "first_intent": first.get("intent"),
                    "first_outcome": outcome, "options": ";".join(options),
                    "target_in_options": code in options,
                    "single_turn_correct": correct(ablation, code),
                    "ablation_status": ablation.get("status"),
                    "with_clarification_correct": correct(final, code),
                    "replied": replied, "final_status": final.get("status"),
                })
    return rows


def summarise(rows):
    by_level = defaultdict(list)
    for r in rows:
        by_level[r["level"]].append(r)
    summary = []
    for level, label in LEVELS:
        rs = by_level[level]
        n = len(rs)
        single = sum(r["single_turn_correct"] for r in rs)
        clar = sum(r["with_clarification_correct"] for r in rs)
        counts = Counter(r["first_outcome"] for r in rs)
        asked = [r for r in rs if r["replied"]]
        recovered = sum(r["with_clarification_correct"] for r in asked)
        summary.append({
            "level": level, "label": label, "n": n,
            "single_turn_correct": single, "single_turn_rate": single / n, "single_turn_ci": wilson_interval(single, n),
            "with_clarification_correct": clar, "with_clarification_rate": clar / n,
            "with_clarification_ci": wilson_interval(clar, n),
            "first_turn": {o: counts.get(o, 0) for o in OUTCOMES},
            "asked": len(asked), "recovered_when_asked": recovered,
            "recovery_rate": recovered / len(asked) if asked else None,
        })
    by_frame = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_frame[r["frame"]][r["level"]].append(r)
    frames = {f: {lvl: sum(x["with_clarification_correct"] for x in rs) / len(rs) for lvl, rs in lv.items()}
              for f, lv in by_frame.items()}
    frames_single = {f: {lvl: sum(x["single_turn_correct"] for x in rs) / len(rs) for lvl, rs in lv.items()}
                     for f, lv in by_frame.items()}
    return summary, frames, frames_single


def render(summary, frames, frames_single, path: Path, note: str) -> None:
    from app.evaluation.figures import GRID, INK, INK_2, SURFACE, _finish, _pyplot, _style

    plt = _pyplot()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.25, 1.15, 1.1]})
    xs = [s["level"] for s in summary]
    ticks = ["0\ncode", "1\nfull name", "2\nno series", "3\ntopic word", "4\nno topic"]

    ax = axes[0]
    _style(ax)
    for key, colour, marker, label in (("single_turn", "#eb6834", "s", "Clarification disabled"),
                                        ("with_clarification", "#2a78d6", "o", "With one clarification reply")):
        rates = [s[f"{key}_rate"] for s in summary]
        lows = [s[f"{key}_ci"][0] for s in summary]
        highs = [s[f"{key}_ci"][1] for s in summary]
        ax.fill_between(xs, lows, highs, color=colour, alpha=0.12, linewidth=0)
        ax.plot(xs, rates, marker=marker, color=colour, linewidth=2, markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=label)
        for x, r in zip(xs, rates):
            ax.text(x, r + (0.045 if key == "with_clarification" else -0.075), f"{r * 100:.0f}%",
                    ha="center", fontsize=7.5, color=colour)
    rec = [(s["level"], s["recovery_rate"], s["recovered_when_asked"], s["asked"]) for s in summary if s["asked"]]
    ax.plot([r[0] for r in rec], [r[1] for r in rec], linestyle=":", marker="D", color="#1baf7a", linewidth=2,
            markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.2, label="Recovered, among prompts where it asked")
    for x, rate, k, n in rec:
        ax.text(x + 0.12, rate + 0.035, f"{k}/{n}", fontsize=7, color="#12805a")
    ax.set_xticks(xs, ticks, fontsize=7.5)
    ax.set_ylim(-0.05, 1.1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_ylabel("Final answer is about the intended module", fontsize=8, color=INK_2)
    ax.set_xlabel("Ambiguity of the question", fontsize=8, color=INK_2)
    ax.set_title("Accuracy as ambiguity rises", fontsize=10, color=INK, loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=7.2, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)

    ax = axes[1]
    _style(ax)
    colours = {"answered_correct": "#1baf7a", "answered_wrong": "#e34948", "asked_with_options": "#2a78d6",
               "asked_generic": "#9fc3ed", "refused": "#8f8e88", "other": "#d9d8d3"}
    labels = {"answered_correct": "Answered, right module", "answered_wrong": "Answered, wrong module or intent",
              "asked_with_options": "Asked, offered candidate modules", "asked_generic": "Asked, no candidates",
              "refused": "Refused as out of scope", "other": "Other"}
    bottom = [0.0] * len(xs)
    for outcome in OUTCOMES:
        vals = [s["first_turn"][outcome] / s["n"] for s in summary]
        if not any(vals):
            continue
        ax.bar(xs, vals, 0.62, bottom=bottom, color=colours[outcome], edgecolor=SURFACE, linewidth=1.5,
               label=labels[outcome])
        for x, v, b in zip(xs, vals, bottom):
            if v >= 0.08:
                ax.text(x, b + v / 2, f"{v * 100:.0f}%", ha="center", va="center", fontsize=7,
                        color="#ffffff" if outcome in {"answered_wrong", "asked_with_options", "refused", "answered_correct"} else INK)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xticks(xs, ticks, fontsize=7.5)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.5, 1], ["0%", "50%", "100%"])
    ax.set_xlabel("Ambiguity of the question", fontsize=8, color=INK_2)
    ax.set_title("What the system did on the first turn", fontsize=10, color=INK, loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)

    ax = axes[2]
    _style(ax)
    palette = ["#2a78d6", "#eb6834", "#1baf7a", "#e87ba4"]
    for i, ((frame, series), colour) in enumerate(zip(frames.items(), palette)):
        ys = [series[x] for x in xs]
        ax.plot([x + (i - 1.5) * 0.07 for x in xs], ys, marker="o", color=colour, linewidth=2, markersize=7, markeredgecolor=SURFACE,
                markeredgewidth=1.2, label=f"“{frame.format(x='X')}”")
    ax.set_xticks(xs, ticks, fontsize=7.5)
    ax.set_ylim(-0.05, 1.1)
    ax.set_yticks([0, 0.5, 1], ["0%", "50%", "100%"])
    ax.set_xlabel("Ambiguity of the question", fontsize=8, color=INK_2)
    ax.set_title("With clarification, by phrasing", fontsize=10, color=INK, loc="left", fontweight="bold")
    ax.text(0.99, 0.55, "Points are offset sideways\nso identical lines stay visible", transform=ax.transAxes,
            ha="right", fontsize=7, color=INK_2)
    ax.legend(frameon=False, fontsize=7.2, loc="lower left")

    _finish(fig, path, "Does clarification recover accuracy as questions get more ambiguous?", draft=False,
            subtitle=note)
    fig.text(0.99, 0.01, "DIAGNOSTIC: developer-generated prompts and replies; not the frozen evaluation",
             ha="right", fontsize=7.5, color=INK_2, style="italic")
    fig.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="baseline", help="Name for this run's output folder.")
    parser.add_argument("--set", choices=sorted(SETS), default="development",
                        help="development: the prompts studied while diagnosing; heldout: unseen families and phrasings.")
    parser.add_argument("--reply", choices=("name", "code"), default="name",
                        help="What the simulated student says when asked which module: its full name or its code.")
    args = parser.parse_args()
    global TARGETS, FRAMES
    TARGETS, FRAMES = SETS[args.set]

    os.environ["GEMINI_API_KEY"] = ""  # deterministic extraction only: one path, no quota
    from fastapi.testclient import TestClient
    from scripts.run_evaluation import _curricupath_components

    service, app = _curricupath_components()
    names = {code: service.repository.get_module(code)["course_name"] for code, *_ in TARGETS}
    with TestClient(app) as client:
        rows = run(client, names, args.reply)
    summary, frames, frames_single = summarise(rows)

    out = OUTPUT / args.label
    out.mkdir(parents=True, exist_ok=True)
    with (out / "prompts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out / "summary.json").write_text(json.dumps(
        {"label": args.label, "set": args.set, "reply": args.reply, "n_prompts": len(rows), "targets": len(TARGETS), "frames": FRAMES,
         "levels": summary, "with_clarification_by_frame": frames, "single_turn_by_frame": frames_single},
        indent=2) + "\n", encoding="utf-8")
    note = (f"{args.set} set, reply = module {args.reply}. {len(TARGETS)} target modules x {len(LEVELS)} levels x {len(FRAMES)} phrasings = {len(rows)} prompts "
            "per curve. Bands: 95% Wilson intervals (prompts share targets, so they are optimistic).")
    render(summary, frames, frames_single, out / "clarification_curve.png", note)

    print(f"{'level':34s} {'clarification off':>12s} {'with clarif.':>13s}   first-turn outcomes")
    for s in summary:
        print(f"{s['level']} {s['label']:32s} {s['single_turn_rate'] * 100:10.0f}% {s['with_clarification_rate'] * 100:12.0f}%   "
              + ", ".join(f"{k}={v}" for k, v in s["first_turn"].items() if v))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
