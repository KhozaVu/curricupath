"""Assemble the checked paper and appendices without modifying component PDFs."""
from pathlib import Path
import json
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject

P = Path(__file__).resolve().parent
PARTS = [
    ("Technical paper", "CurricuPath_Gift_Vundla_Main_Paper.pdf", 6),
    ("Appendix A - Team reflection and actual work distribution", "Reflection_on_Group_Work.pdf", 2),
    ("Appendix B - Original unmarked project plan", "Appendix_B_Original_Unmarked_Project_Plan.pdf", 11),
    ("Appendix C - Application use-case demonstrations", "Appendix_C_Application_Use_Cases.pdf", 3),
    ("Appendix D - Engine integration and verification", "Appendix_D_Integration_and_Verification.pdf", 3),
    ("Appendix E - Merged meeting minutes", "Appendix_E_Merged_Meeting_Minutes.pdf", 27),
]


def namespace_destinations(reader, prefix):
    """Keep repeated LaTeX destination names local to their component."""
    names = {name: prefix + name for name in reader.named_destinations}

    def rename_tree(node):
        node = node.get_object()
        if "/Names" in node:
            entries = node["/Names"]
            for i in range(0, len(entries), 2):
                old = str(entries[i])
                entries[i] = TextStringObject(names.get(old, prefix + old))
        for child in node.get("/Kids", []):
            rename_tree(child)

    root = reader.trailer["/Root"]
    if "/Names" in root and "/Dests" in root["/Names"]:
        rename_tree(root["/Names"]["/Dests"])
    if "/Dests" in root:
        dests = root["/Dests"]
        for key in list(dests):
            value = dests.pop(key)
            dests[NameObject("/" + prefix + str(key).lstrip("/"))] = value

    def rename_target(container, key):
        value = container.get(key)
        if isinstance(value, str) and value in names:
            container[NameObject(key)] = TextStringObject(names[value])

    for page in reader.pages:
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            rename_target(annotation, "/Dest")
            action = annotation.get("/A")
            if action is not None:
                action = action.get_object()
                if action.get("/S") == "/GoTo":
                    rename_target(action, "/D")
    # PdfReader caches its name tree; refresh after the in-memory renaming.
    reader._named_destinations_cache = None
    return names


def assemble():
    writer = PdfWriter()
    sections = []
    offset = 0
    destination_expectations = {}
    for part_index, (title, filename, expected) in enumerate(PARTS):
        reader = PdfReader(P / filename)
        if len(reader.pages) != expected:
            raise ValueError(f"{filename}: expected {expected} pages, found {len(reader.pages)}")
        prefix = f"part{part_index}."
        for name, destination in reader.named_destinations.items():
            destination_expectations[prefix + name] = offset + reader.get_destination_page_number(destination)
        namespace_destinations(reader, prefix)
        writer.append(reader, import_outline=False)
        writer.add_outline_item(title, offset)
        sections.append({"section": title, "start_page": offset + 1, "pages": expected})
        offset += expected
    writer.add_metadata({
        "/Title": "AI-Assisted E-Learning Recommendation Platform",
        "/Author": "Gift Vundla (2550723)",
        "/Subject": "Wits curriculum eligibility investigation; technical paper and Appendices A-E",
    })
    target = P / "CurricuPath_Gift_Vundla_Report.pdf"
    temporary = P / "CurricuPath_Gift_Vundla_Report.assembled.pdf"
    writer.write(temporary)
    writer.close()
    merged = PdfReader(temporary)
    if len(merged.pages) != offset:
        raise ValueError("Combined page count changed")
    for name, expected in destination_expectations.items():
        destination = merged.named_destinations.get(name)
        if destination is None or merged.get_destination_page_number(destination) != expected:
            raise ValueError(f"Incorrect merged navigation target: {name}")
    index = 0
    for _, filename, _ in PARTS:
        for original in PdfReader(P / filename).pages:
            if original.extract_text() != merged.pages[index].extract_text():
                raise ValueError(f"Text mismatch on combined page {index + 1}")
            index += 1
    temporary.replace(target)
    (P / "report_sections.json").write_text(json.dumps({
        "total_pages": offset, "main_paper_pages": 6, "sections": sections,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Assembled {offset} pages; component text, {len(destination_expectations)} named targets and six section bookmarks checked.")


if __name__ == "__main__":
    assemble()
