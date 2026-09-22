"""Extract verified handbook/CBO pages into the pgvector evaluation corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from sqlalchemy import delete, insert, select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.data.database import create_database_engine
from app.data.loaders import load_curriculum_data
from app.data.schema import document_chunks


EVALUATION_DIRECTORY = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"


def _page_chunks(text: str, words_per_chunk: int, overlap: int) -> list[str]:
    words = re.sub(r"\s+", " ", text).strip().split()
    if not words:
        return []
    step = words_per_chunk - overlap
    return [
        " ".join(words[start : start + words_per_chunk])
        for start in range(0, len(words), step)
        if words[start : start + words_per_chunk]
    ]


def build_corpus_rows(
    words_per_chunk: int = 900,
    overlap: int = 150,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return source-grounded rows and extraction notes without encoded rules."""

    data = load_curriculum_data(PROJECT_ROOT / "data" / "processed")
    relevant_source_ids = {"EBE_2026"}
    relevant_source_ids.update(
        row["source_id"]
        for row in data.cbo_courses
        if row["curriculum_status"] == "current"
    )
    rows: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    for source in data.sources:
        if source["source_id"] not in relevant_source_ids:
            continue
        if source["verification_status"] != "verified":
            notes.append(
                {
                    "source_id": source["source_id"],
                    "status": "skipped_unverified",
                }
            )
            continue
        local_path = source["local_path"].strip()
        path = PROJECT_ROOT / local_path if local_path else None
        if path is None or path.suffix.lower() != ".pdf" or not path.exists():
            notes.append(
                {
                    "source_id": source["source_id"],
                    "status": "skipped_no_extractable_pdf",
                    "path": local_path,
                }
            )
            continue

        extracted = 0
        reader = PdfReader(str(path))
        offset = int(source["handbook_page_offset"] or 0)
        for pdf_page, page in enumerate(reader.pages, start=1):
            printed_page = pdf_page - offset if offset else pdf_page
            page_text = page.extract_text() or ""
            for chunk_number, chunk_text in enumerate(
                _page_chunks(page_text, words_per_chunk, overlap)
            ):
                locator = f"pdf_page_{pdf_page}_printed_{printed_page}"
                item_id = (
                    f"{source['source_id']}::{locator}::chunk_{chunk_number:02d}"
                )
                content = (
                    f"Source {source['source_id']}; PDF page {pdf_page}; "
                    f"printed page {printed_page}. {chunk_text}"
                )
                item_type = (
                    "evaluation_handbook"
                    if source["source_id"] == "EBE_2026"
                    else "evaluation_cbo"
                )
                rows.append(
                    {
                        "item_type": item_type,
                        "item_id": item_id,
                        "chunk_kind": "raw_pdf_page",
                        "content": content,
                        "content_hash": hashlib.sha256(
                            content.encode("utf-8")
                        ).hexdigest(),
                        "source_id": source["source_id"],
                    }
                )
                extracted += 1
        notes.append(
            {
                "source_id": source["source_id"],
                "status": "extracted",
                "path": local_path,
                "chunks": extracted,
            }
        )
    return rows, notes


def replace_evaluation_corpus(rows: list[dict[str, Any]]) -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    with engine.begin() as connection:
        cached = {
            (row["item_id"], row["content_hash"]): row
            for row in connection.execute(
                select(document_chunks).where(
                    document_chunks.c.item_type.in_(
                        ("evaluation_source", "evaluation_handbook", "evaluation_cbo")
                    )
                )
            ).mappings()
        }
        connection.execute(
            delete(document_chunks).where(
                document_chunks.c.item_type.in_(
                    ("evaluation_source", "evaluation_handbook", "evaluation_cbo")
                )
            )
        )
        for row in rows:
            old = cached.get((row["item_id"], row["content_hash"]))
            if old is not None:
                row.update(
                    {
                        "embedding_provider": old["embedding_provider"],
                        "embedding_model": old["embedding_model"],
                        "embedding_dimension": old["embedding_dimension"],
                        "embedding": old["embedding"],
                        "embedded_at": old["embedded_at"],
                    }
                )
        if rows:
            connection.execute(insert(document_chunks), rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--words-per-chunk", type=int, default=900)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Build the manifest without replacing PostgreSQL rows.",
    )
    args = parser.parse_args()
    if args.words_per_chunk <= args.overlap or args.overlap < 0:
        raise SystemExit("words-per-chunk must be greater than a non-negative overlap.")

    rows, notes = build_corpus_rows(args.words_per_chunk, args.overlap)
    if not rows:
        raise SystemExit("No verified PDF text was extracted for the evaluation corpus.")
    if not args.extract_only:
        replace_evaluation_corpus(rows)

    EVALUATION_DIRECTORY.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "item_types": {
            "eligibility": "evaluation_handbook",
            "grounding": "evaluation_cbo"
        },
        "words_per_chunk": args.words_per_chunk,
        "overlap_words": args.overlap,
        "chunk_count": len(rows),
        "corpus_sha256": hashlib.sha256(
            "\n".join(row["content_hash"] for row in rows).encode("utf-8")
        ).hexdigest(),
        "sources": notes,
        "database_updated": not args.extract_only,
    }
    (EVALUATION_DIRECTORY / "corpus_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Evaluation chunks: {len(rows)}")
    print(f"Database updated: {not args.extract_only}")


if __name__ == "__main__":
    main()
