#!/usr/bin/env python3
"""
Main CLI runner for the Agentic GraphRAG pipeline.

Usage:
    # Process documents and start interactive Q&A
    python run_pipeline.py data/documents/

    # Process specific files
    python run_pipeline.py report.docx notes.txt spec.md

    # Process and skip NLP (faster, vector-only RAG)
    python run_pipeline.py --skip-nlp data/documents/

    # Just run Q&A on previously processed data
    python run_pipeline.py --query-only
"""

import argparse
import logging
import sys

from src.pipeline import AgenticPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agentic GraphRAG Pipeline - Document Q&A with Knowledge Graphs",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="File paths or directories to process (.docx, .txt, .md)",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config file (default: config.toml)",
    )
    parser.add_argument(
        "--domain",
        default="domain.json",
        help="Path to domain config (default: domain.json)",
    )
    parser.add_argument(
        "--skip-nlp",
        action="store_true",
        help="Skip NLP entity extraction (faster, vector-only)",
    )
    parser.add_argument(
        "--query-only",
        action="store_true",
        help="Skip processing, only run Q&A on existing data",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Run a single query and exit",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check prerequisites and exit",
    )

    args = parser.parse_args()

    pipeline = AgenticPipeline(
        config_path=args.config,
        domain_path=args.domain,
    )

    # Check mode
    if args.check:
        status = pipeline.check_prerequisites()
        for key, val in status.items():
            icon = "OK" if val else "MISSING"
            print(f"  [{icon}] {key}")
        sys.exit(0 if all(status.values()) else 1)

    # Query-only mode
    if args.query_only:
        pipeline.initialize()
        if args.query:
            result = pipeline.query(args.query)
            print(f"\nA: {result['answer']}")
        else:
            pipeline.interactive()
        return

    # Full pipeline
    if not args.inputs:
        parser.error("Please provide input files or directories, or use --query-only")

    summary = pipeline.run(args.inputs, skip_nlp=args.skip_nlp)

    print(f"\nPipeline Summary:")
    print(f"  Documents: {summary['documents_loaded']}")
    print(f"  Paragraphs: {summary['total_paragraphs']}")
    print(f"  Chunks: {summary['chunks_stored']}")

    # Single query or interactive
    if args.query:
        result = pipeline.query(args.query)
        print(f"\nQ: {result['question']}")
        print(f"A: {result['answer']}")
    else:
        pipeline.interactive()


if __name__ == "__main__":
    main()
