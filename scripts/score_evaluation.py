"""Score frozen v2.5 evaluation outputs; write report tables and figures."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
RAW = EVALUATION / "results" / "raw"
BRIEFING_LABELS = EVALUATION / "pilot" / "senate_briefing_labels.csv"

from app.evaluation import figures, report, scoring
from scripts.check_evaluation_readiness import readiness_errors


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True,
        capture_output=True, check=False,
    ).stdout.strip()


def _reference_sets(names, cases, provenance):
    """Developer labels, optionally alongside the developer-side Senate Rules briefing labels."""

    sets = {}
    if "developer" in names:
        sets["developer"] = (cases, {**provenance, "label_set": "developer"})
    if "briefing" in names:
        sets["briefing"] = scoring.apply_label_set(
            cases,
            scoring.load_label_set(BRIEFING_LABELS, "briefing_label"),
            name="briefing",
            description=(
                "briefing_draft: developer-side Senate Rules briefing labels, unattributed "
                "(NOT independent evidence)"
            ),
        )
    return sets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-draft", action="store_true",
        help="Score draft_*.jsonl against developer labels. Output is marked DRAFT.",
    )
    parser.add_argument(
        "--reference-sets", nargs="+", choices=("developer", "briefing"), default=["developer"],
        help="Draft only. Score against developer expected labels, the Senate Rules briefing "
             "labels, or both (adds a sensitivity comparison).",
    )
    parser.add_argument("--arms", nargs="+", choices=figures.ARM_ORDER, default=list(figures.ARM_ORDER))
    parser.add_argument("--bootstrap", type=int, default=scoring.DEFAULT_BOOTSTRAP)
    parser.add_argument("--seed", type=int, default=scoring.DEFAULT_SEED)
    parser.add_argument("--no-figures", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    if not args.allow_draft:
        if args.reference_sets != ["developer"]:
            raise SystemExit("Alternate label sets are draft-only; official scoring uses approved reviewer labels.")
        # Raw outputs are untracked until committed, so a clean tree is not required here.
        errors = readiness_errors(require_clean_git=False)
        if errors:
            raise SystemExit("Official scoring blocked:\n- " + "\n- ".join(errors))

    prefix = "draft_" if args.allow_draft else ""
    output_dir = args.output_dir or (
        EVALUATION / "results" / ("draft_analysis" if args.allow_draft else "analysis")
    )
    cases, provenance = scoring.load_reference_cases(
        EVALUATION / "eligibility_cases.csv", draft=args.allow_draft
    )

    observations, hashes, absent = {}, {}, []
    for arm in args.arms:
        path = RAW / f"{prefix}{arm}.jsonl"
        if not path.exists():
            absent.append(arm)
            continue
        observations[arm] = scoring.read_observations(path)
        hashes[path.name] = _sha256(path)
    if not observations:
        raise SystemExit(f"No {prefix}*.jsonl outputs found in {RAW}.")
    if absent:
        print(f"Not scored (no output file): {', '.join(absent)}")

    hashes["eligibility_cases.csv"] = _sha256(EVALUATION / "eligibility_cases.csv")
    if "briefing" in args.reference_sets:
        hashes[BRIEFING_LABELS.name] = _sha256(BRIEFING_LABELS)
    inputs = {"git_head": _git_head(), "sha256": hashes, "arms_without_output": absent}

    sets = _reference_sets(args.reference_sets, cases, provenance) if args.allow_draft else {
        "official": (cases, provenance)}
    multiple = len(sets) > 1
    results, written = {}, []
    for name, (set_cases, set_provenance) in sets.items():
        summary = scoring.score(set_cases, observations, n_boot=args.bootstrap, seed=args.seed)
        results[name] = (summary, set_provenance)
        target = output_dir / name if multiple else output_dir
        written += report.write_outputs(
            summary, set_provenance, set_cases, target, draft=args.allow_draft, inputs=inputs
        )
        if not args.no_figures:
            try:
                written += figures.render_all(summary, target / "figures", draft=args.allow_draft)
            except RuntimeError as error:
                print(f"Figures skipped: {error}")
        print(f"\nReference: {name}")
        for arm, data in summary["arms"].items():
            print(f"  {arm:32s} macro-F1 {data['macro_f1']:.3f}  balanced acc "
                  f"{data['balanced_accuracy']:.3f}  missing {len(data['missing_cases'])}")
            if data["provider_failure_cases"]:
                print(f"    WARNING: {len(data['provider_failure_cases'])} runs were refused by the "
                      "hosted service (quota or outage), not answered wrongly. Re-run before interpreting.")

    if multiple:
        first, second = list(sets)
        a = [c["reference_label"] for c in sets[first][0]]
        b = [c["reference_label"] for c in sets[second][0]]
        agreement = scoring.label_set_agreement(a, b)
        differences = [(c["case_id"], x, y) for c, x, y in zip(sets[first][0], a, b) if x != y]
        written += report.write_sensitivity(results, agreement, differences, output_dir)
        if not args.no_figures:
            figure_dir = output_dir / "figures"
            figure_dir.mkdir(parents=True, exist_ok=True)
            try:
                figures.label_set_sensitivity(
                    {name: summary for name, (summary, _) in results.items()},
                    figure_dir / "fig8_label_set_sensitivity.png", draft=True,
                )
            except RuntimeError as error:
                print(f"Sensitivity figure skipped: {error}")
        print(f"\nLabel sets agree on {agreement['raw_agreement'] * 100:.0f}% of cases "
              f"(kappa {agreement['cohens_kappa']:.2f}); they differ on {len(differences)}.")

    if args.allow_draft:
        print(f"\n{figures.DRAFT_NOTE}.")
    print(f"Wrote {len(written)} files under {output_dir}")


if __name__ == "__main__":
    main()
