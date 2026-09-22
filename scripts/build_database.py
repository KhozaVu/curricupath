"""Build and transactionally import the PostgreSQL CurricuPath catalogue."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.data.database import (
    create_database_engine,
    database_status,
    replace_catalogue,
    upgrade_database,
)
from app.data.loaders import load_curriculum_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Apply migrations without importing the CSV catalogue.",
    )
    args = parser.parse_args()
    settings = get_settings()

    print("Applying PostgreSQL migrations...")
    upgrade_database(settings.database_url, PROJECT_ROOT)
    engine = create_database_engine(settings.database_url)

    if not args.schema_only:
        print("Validating and importing processed CSV data...")
        data = load_curriculum_data(settings.processed_data_directory)
        counts = replace_catalogue(engine, data)
        for table, count in counts.items():
            print(f"{table}: {count}")

    status = database_status(engine)
    print("Database ready")
    print(f"pgvector: {status['vector_extension_version']}")
    print(f"tables: {status['table_count']}")
    print(f"modules: {status['module_count']}")
    print(f"search chunks: {status['document_chunk_count']}")
    print(f"embedded chunks: {status['embedded_chunk_count']}")


if __name__ == "__main__":
    main()
