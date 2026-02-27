#!/usr/bin/env python3
"""
Search debugging tool for GraphRAG-Senzing
Helps identify why certain terms are not being found.
"""

import json
import pathlib
import sys
import tomllib

import lancedb
import polars as pl


def load_config(config_path: str = "config.toml") -> dict:
    """Load configuration."""
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def search_in_entities(term: str, config: dict) -> None:
    """Search for term in entity store."""
    ent_path = pathlib.Path(config["ent"]["store_path"])

    if not ent_path.exists():
        print(f"❌ Entity file not found: {ent_path}")
        return

    entities = []
    with open(ent_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entities.append(json.loads(line))

    print(f"\n{'=' * 60}")
    print(f"🔍 Searching entities for: '{term}'")
    print(f"{'=' * 60}\n")

    matches = [
        e for e in entities
        if term.lower() in e.get("text", "").lower()
        or term.lower() in e.get("lemma_key", "").lower()
    ]

    if matches:
        print(f"✓ Found {len(matches)} entity matches:\n")
        for e in matches[:10]:
            print(f"  - {e.get('text', '')} [{e.get('label', '?')}]")
            print(f"    Count: {e.get('count', 0)}, Lemma: {e.get('lemma_key', '')}")
    else:
        print(f"❌ No entity matches found")
        print(f"\nTop 20 entities (by frequency):")
        top_entities = sorted(entities, key=lambda x: x.get("count", 0), reverse=True)[:20]
        for e in top_entities:
            print(f"  - {e.get('text', '')} [{e.get('label', '?')}] × {e.get('count', 0)}")


def search_in_chunks(term: str, config: dict) -> None:
    """Search for term in vector store chunks."""
    lancedb_uri = config["vect"]["lancedb_uri"]
    table_name = config["vect"]["chunk_table"]

    db_path = pathlib.Path(lancedb_uri)
    if not db_path.exists():
        print(f"\n❌ LanceDB not found: {db_path}")
        return

    try:
        db = lancedb.connect(str(db_path))
        table = db.open_table(table_name)
    except Exception as e:
        print(f"\n❌ Failed to open LanceDB: {e}")
        return

    print(f"\n{'=' * 60}")
    print(f"🔍 Searching chunks for: '{term}'")
    print(f"{'=' * 60}\n")

    # Get all chunks
    df = pl.from_arrow(table.to_arrow())

    # Filter chunks containing the term
    matches = df.filter(pl.col("text").str.to_lowercase().str.contains(term.lower()))

    if len(matches) > 0:
        print(f"✓ Found {len(matches)} chunk matches:\n")
        for row in matches.head(5).iter_rows(named=True):
            print(f"  Chunk ID: {row['uid']}")
            print(f"  Source: {pathlib.Path(row['source']).name}")
            print(f"  Text preview: {row['text'][:200]}...")
            print()
    else:
        print(f"❌ No chunk matches found")
        print(f"\nShowing 3 random chunks for reference:")
        for row in df.head(3).iter_rows(named=True):
            print(f"  - {row['text'][:100]}...")


def main():
    """Main search debugging workflow."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Debug GraphRAG search - find why terms are not being found",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for "백신휴가" in entities and chunks
  python tools/search_debug.py "백신휴가"

  # Search for "재택근무"
  python tools/search_debug.py "재택근무"
        """,
    )

    parser.add_argument(
        "term",
        help="Search term to look for",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Config file path (default: config.toml)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    print(f"\n{'#' * 60}")
    print(f"# GraphRAG Search Debugger")
    print(f"# Term: {args.term}")
    print(f"{'#' * 60}")

    # Search in entities
    search_in_entities(args.term, config)

    # Search in chunks
    search_in_chunks(args.term, config)

    print(f"\n{'=' * 60}")
    print("💡 Recommendations:")
    print("=" * 60)
    print("1. If term NOT in chunks → Document not loaded or term not in source")
    print("2. If term IN chunks but NOT in entities → NLP didn't extract it")
    print("3. If term IN both → Embedding similarity issue (try exact phrase)")
    print("4. Check chunk_size in config.toml (smaller = more precise)")
    print()


if __name__ == "__main__":
    main()
