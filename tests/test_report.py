"""Tests for evaluation report tables and figures."""

from __future__ import annotations

import csv
import json

import pytest

from app.evaluation import report, scoring as s


E, I, M = "eligible", "ineligible", "manual_review_required"
PROVENANCE = {"mode": "draft", "reference_source": "developer_expected_label (NOT independent evidence)",
              "rejected_cases": []}


def _cases(n=12):
    return [
        {"case_id": f"C{i}", "reference_label": label, "author_source": "developer_drafted",
         "scenario_type": "t", "clarification_permitted": "false"}
        for i, label in enumerate([E, I, M] * (n // 3))
    ]


def _summary(cases):
    def obs(arm, wrong=()):
        return [
            s.Observation(c["case_id"], arm, 1, I if c["case_id"] in wrong else c["reference_label"], 5, "valid", None)
            for c in cases
        ]
    return s.score(cases, {"curricupath": obs("curricupath"), "handbook_rag": obs("handbook_rag", {"C0", "C2"})},
                   n_boot=50)


def test_markdown_carries_draft_banner_and_names_what_is_not_computed() -> None:
    cases = _cases()
    text = report.markdown(_summary(cases), PROVENANCE, draft=True)

    assert "DRAFT" in text.splitlines()[2]
    assert "Do not cite" in text
    assert "Material-reason completeness" in text
    assert "CurricuPath minus Handbook RAG" in text


def test_official_markdown_has_no_draft_banner() -> None:
    cases = _cases()
    text = report.markdown(_summary(cases), {**PROVENANCE, "mode": "official"}, draft=False)

    assert "Do not cite" not in text


def test_write_outputs_creates_tables_with_blank_failure_categories(tmp_path) -> None:
    cases = _cases()
    written = report.write_outputs(_summary(cases), PROVENANCE, cases, tmp_path, draft=True,
                                   inputs={"git_head": "abc", "sha256": {}})

    assert {p.name for p in written} == {
        "metrics_summary.json", "arm_metrics.csv", "paired_differences.csv",
        "stratified_accuracy.csv", "case_decisions.csv", "report_tables.md"}
    with (tmp_path / "case_decisions.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert {r["failure_category"] for r in rows} == {""}
    assert rows[0]["handbook_rag_correct"] == "False"
    saved = json.loads((tmp_path / "metrics_summary.json").read_text(encoding="utf-8"))
    assert saved["draft"] is True and "decisions_by_case" not in saved


def test_figures_render_when_matplotlib_is_available(tmp_path) -> None:
    pytest.importorskip("matplotlib")
    from app.evaluation import figures

    cases = _cases()
    written = figures.render_all(_summary(cases), tmp_path, draft=True)

    assert {p.name for p in written} >= {"fig1_primary_metrics.png", "fig2_confusion_matrices.png",
                                          "fig3_error_types.png", "fig4_latency.png",
                                          "fig6_paired_differences.png", "fig7_accuracy_by_subset.png"}
    assert all(p.stat().st_size > 5_000 for p in written)


def test_figures_fail_with_a_clear_message_without_matplotlib(monkeypatch, tmp_path) -> None:
    import builtins

    from app.evaluation import figures

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.startswith("matplotlib"):
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)

    with pytest.raises(RuntimeError, match="matplotlib is required"):
        figures.render_all(_summary(_cases()), tmp_path, draft=True)


def _two_sets():
    cases = _cases()
    other = [{**c, "reference_label": M if c["reference_label"] == E else c["reference_label"]} for c in cases]
    results = {
        "developer": (_summary(cases), {**PROVENANCE, "reference_source": "developer labels"}),
        "briefing": (_summary(other), {**PROVENANCE, "reference_source": "briefing labels"}),
    }
    a = [c["reference_label"] for c in cases]
    b = [c["reference_label"] for c in other]
    differences = [(c["case_id"], x, y) for c, x, y in zip(cases, a, b) if x != y]
    return results, s.label_set_agreement(a, b), differences


def test_sensitivity_report_states_agreement_verdict_changes_and_disagreeing_cases(tmp_path) -> None:
    results, agreement, differences = _two_sets()

    written = report.write_sensitivity(results, agreement, differences, tmp_path)
    text = (tmp_path / "label_set_sensitivity.md").read_text(encoding="utf-8")

    assert {p.name for p in written} == {"label_set_sensitivity.csv", "label_set_sensitivity.md"}
    assert "neither is independent evidence" in text
    assert f"They differ on {len(differences)} cases" in text
    assert "Does the comparison verdict change?" in text
    assert "| C0 | eligible | manual_review_required |" in text


def test_sensitivity_figure_renders(tmp_path) -> None:
    pytest.importorskip("matplotlib")
    from app.evaluation import figures

    results, _, _ = _two_sets()
    path = tmp_path / "fig8.png"
    figures.label_set_sensitivity({k: v[0] for k, v in results.items()}, path, draft=True)

    assert path.stat().st_size > 5_000


def test_markdown_warns_when_runs_failed_at_the_provider() -> None:
    cases = _cases()
    summary = _summary(cases)
    summary["arms"]["handbook_rag"]["provider_failure_cases"] = ["C0", "C1"]

    text = report.markdown(summary, PROVENANCE, draft=True)

    assert "Warning: provider failures" in text
    assert "'handbook_rag': 2" in text
