"""Generate hosted embeddings for pending PostgreSQL catalogue chunks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.data.database import create_database_engine
from app.data.embeddings import HuggingFaceHostedEmbeddings, embed_catalogue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate vectors even when provider, model, and dimension match.",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.hf_token:
        raise SystemExit("HF_TOKEN is not configured in the environment or .env file.")
    if settings.embedding_provider != "huggingface":
        raise SystemExit(
            "Only EMBEDDING_PROVIDER=huggingface is supported by this hosted adapter."
        )

    provider = HuggingFaceHostedEmbeddings(
        settings.hf_token,
        settings.embedding_model,
        settings.embedding_dimension,
    )
    engine = create_database_engine(settings.database_url)
    report = embed_catalogue(
        engine,
        provider,
        batch_size=args.batch_size,
        force=args.force,
    )
    print(f"Selected chunks: {report.selected}")
    print(f"Embedded chunks: {report.embedded}")
    print(f"Completed batches: {report.batches}")
    print(f"Hosted model: {provider.model_name} ({provider.dimension} dimensions)")


if __name__ == "__main__":
    main()
