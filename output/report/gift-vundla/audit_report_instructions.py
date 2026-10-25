"""Check the current report assets against the accepted document constraints."""
from pathlib import Path
from hashlib import sha256
import json
import re
import xml.etree.ElementTree as ET
from pypdf import PdfReader

P = Path(__file__).resolve().parent


def audit():
    main = (P / "CurricuPath_Gift_Vundla_Report.tex").read_text(encoding="utf-8")
    reflection = (P / "Reflection_on_Group_Work.tex").read_text(encoding="utf-8")
    shared = json.loads((P / "shared_results.json").read_text())
    keys = re.findall(r"\\bibitem\{([^}]+)\}", main)
    cites = [key for group in re.findall(r"\\cite(?:\[[^]]*\])?\{([^}]+)\}", main)
             for key in group.split(",")]
    bibliography = main[main.index(r"\begin{thebibliography}"):
                        main.index(r"\end{thebibliography}") + len(r"\end{thebibliography}")]
    tables = "\n\n".join(re.findall(r"\\begin\{table\}.*?\\end\{table\}", main, re.S))
    assert (P / "shared_references.tex").read_text(encoding="utf-8").strip() == bibliography.replace("\\newpage\n", "")
    assert (P / "shared_tables.tex").read_text(encoding="utf-8").strip() == tables
    assert len(keys) == 22 and set(cites) == set(keys) and cites[0] == "wits"
    expected_keys = ["wits", "empowered", "khalil", "tamas", "nile", "jiang", "chawana", "islam", "ibrahim", "joren", "qulac", "abstention", "fastapi", "react", "alembic", "sqlalchemy", "pgvector", "bge", "gemini", "structured", "grras", "sokolova"]
    assert keys == expected_keys
    sections = re.findall(r"\\section\{([^}]+)\}", main)
    assert sections[1] == "LITERATURE REVIEW" and len(sections) == 7
    assert r"\author{Gift Vundla (2550723)}" in main
    assert "AI-Assisted E-Learning Recommendation Platform" in main
    assert r"\title{AI-Assisted E-Learning Recommendation Platform}" in main
    assert "\\normalsize" not in main.split(r"\author")[0]
    assert len(re.findall(r"\\begin\{table\}", main)) == 2
    assert len(re.findall(r"\\begin\{figure\}", main)) == 2
    assert len(re.findall(r"\\begin\{equation\}", main)) == 2
    assert r"95\% Wilson" in main
    assert "reconcile" not in main.lower() and r"\dagger" not in main
    assert not re.search(r"public[- ]course|anthropic|claude", main, re.I)
    assert main.count(r"\includegraphics") == 2
    for figure in ["shared_evidence.pdf", "shared_clarification.pdf"]:
        assert figure in main
    expected_rows = ["Project planning and scope", "Curriculum data and evidence",
        "Eligibility rule design", "Request interpretation and clarification",
        "Database, retrieval and interface", "Testing and validation",
        "Experimental cases and baselines", "Experimental evaluation",
        "Results and reproducibility", "Documentation and presentation"]
    for row in expected_rows:
        assert reflection.count(row + " &") == 1, row
    for heading in ["A1 Team Reflection", "A2 Changes from the Project Plan",
                    "A3 Actual Work Distribution", "A4 Overall Reflection"]:
        assert heading in reflection
    assert "Change from project plan" in reflection
    assert "Gift Vundla" not in main[main.index(r"\section{INTRODUCTION}"):]
    assert "Vukosi" not in main
    assert all(row["n_per_wording"] == 40 and row["unsafe_denominator"] == 78
               for row in shared["classification"])
    for row in shared["classification"]:
        value = f'{row["mean_macro_f1"]:.3f}'
        assert value in tables
        assert abs(row["mean_macro_f1"] - sum(row["macro_f1_by_wording"]) / 3) < 1e-12
    tests = ET.parse(P / "verification_run_2026-10-23.xml").findall(".//testcase")
    assert len(tests) == 62
    assert sum(t.find("skipped") is not None for t in tests) == 7
    assert not any(t.find("failure") is not None or t.find("error") is not None for t in tests)
    components = {"CurricuPath_Gift_Vundla_Main_Paper.pdf": 6,
        "Reflection_on_Group_Work.pdf": 2,
        "Appendix_B_Original_Unmarked_Project_Plan.pdf": 11,
        "Appendix_C_Application_Use_Cases.pdf": 3,
        "Appendix_D_Integration_and_Verification.pdf": 3,
        "Appendix_E_Merged_Meeting_Minutes.pdf": 27}
    for name, count in components.items():
        assert len(PdfReader(P / name).pages) == count, name
    merged = PdfReader(P / "CurricuPath_Gift_Vundla_Report.pdf")
    assert len(merged.pages) == 52 and len(merged.outline) == 6
    assert len(merged.named_destinations) == sum(len(PdfReader(P / name).named_destinations) for name in components)
    assert all(name.startswith("part") for name in merged.named_destinations)
    assert "Existing or empty conversation context" in (P / "integration_sequence.mmd").read_text()
    diagram_text = "".join(page.extract_text() for page in PdfReader(P / "integration_sequence.pdf").pages)
    assert "Existing or empty conversation context" in diagram_text
    for name, expected in {
        "witseiepaper.cls": "b9732657392fa7f0fa856b120471c55bc53789da522917352ca3bc9c022774b4",
        "KJN.sty": "5ee3196701a085e43d359f687de6e1b8088ac9a53845359025cf69c43c0bf2b2",
    }.items():
        assert sha256((P / name).read_bytes()).hexdigest() == expected
    result = {"date": "2026-10-25", "scope": "Gift's report, appendices and reusable partner assets",
        "automated_constraint_checks": "passed", "main_pages": 6, "combined_pages": 52,
        "main_tables": 2, "main_figures": 2, "equations": 2, "references": 22, "literature_review_section": 2,
        "work_distribution_rows": 10, "reflection_pages": 2,
        "focused_verification": {"passed": 55, "skipped": 7, "failed": 0},
        "external_confirmations": [
            "Identity of supplied unmarked plan as the exact originally submitted file",
            "Partner's final manuscript uses the corrected shared assets"],
        "unexecuted_validation": ["Seven live PostgreSQL comparisons remain skipped"],
        "pdf_sha256": sha256((P / "CurricuPath_Gift_Vundla_Report.pdf").read_bytes()).hexdigest()}
    (P / "instruction_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    audit()
