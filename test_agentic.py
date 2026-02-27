#!/usr/bin/env python3
"""
Test script for Agentic GraphRAG.

Compares standard vs agentic mode on example queries.
"""

import json
import sys
from pathlib import Path

from src.pipeline import AgenticPipeline


def test_agentic_vs_standard():
    """Compare standard and agentic modes."""
    # Test queries (Korean)
    test_queries = [
        "재택근무 승인자는 누구인가요?",
        "누나 결혼하면 경조금은 얼마인가요?",
        "백신휴가는 며칠까지 가능한가요?",
    ]

    print("=" * 80)
    print("AGENTIC GRAPHRAG TEST")
    print("=" * 80)
    print("\nInitializing pipeline...")

    # Initialize pipeline
    pipeline = AgenticPipeline()

    print("Checking prerequisites...")
    status = pipeline.check_prerequisites()
    if not all(status.values()):
        print("ERROR: Prerequisites not met!")
        print(json.dumps(status, indent=2))
        return

    # Check if data already loaded
    if not Path("data/lancedb").exists():
        print("\nERROR: No data found. Run pipeline.run_all() first!")
        print("Example: python -c 'from src.pipeline import AgenticPipeline; p = AgenticPipeline(); p.run_all(\"data/documents\")'")
        return

    # Load existing data
    print("Loading existing data...")
    pipeline.initialize()
    result = pipeline.load_existing_data()

    if not result["success"]:
        print(f"ERROR: {result['message']}")
        return

    print(f"{result['message']}\n")

    # Test each query in both modes
    for i, query in enumerate(test_queries, 1):
        print("\n" + "=" * 80)
        print(f"TEST {i}: {query}")
        print("=" * 80)

        # Standard mode
        print("\n[STANDARD MODE]")
        print("-" * 80)
        try:
            result_std = pipeline.query(query, agentic=False)
            print(f"Answer: {result_std['answer']}")
            print(f"Chunks: {result_std['num_chunks']}")
            print(f"Time: {result_std['elapsed_sec']}s")
        except Exception as e:
            print(f"ERROR: {e}")

        # Agentic mode
        print("\n[AGENTIC MODE]")
        print("-" * 80)
        try:
            result_agentic = pipeline.query(query, agentic=True)
            print(f"Answer: {result_agentic['answer']}")
            if result_agentic.get("validation"):
                val = result_agentic["validation"]
                status = "✓ PASS" if val.get("valid") else "✗ FAIL"
                print(f"Validation: {status} (confidence: {val.get('confidence', 0.0):.2f})")
            print(f"Reasoning steps: {len(result_agentic.get('reasoning_chain', []))}")
            print(f"Citations: {len(result_agentic.get('citations', []))}")
            print(f"Retries: {result_agentic.get('retry_count', 0)}")

            # Show reasoning chain
            if result_agentic.get('reasoning_chain'):
                print("\nReasoning chain:")
                for step in result_agentic['reasoning_chain']:
                    print(f"  Step {step['step']}: {step['answer'][:100]}...")

            # Show execution history
            if result_agentic.get('execution_history'):
                print("\nExecution history:")
                for event in result_agentic['execution_history']:
                    print(f"  • {event}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


def test_interactive_agentic():
    """Run interactive session in agentic mode."""
    print("=" * 80)
    print("AGENTIC GRAPHRAG INTERACTIVE SESSION")
    print("=" * 80)

    pipeline = AgenticPipeline()
    pipeline.initialize()
    result = pipeline.load_existing_data()

    if not result["success"]:
        print(f"ERROR: {result['message']}")
        return

    print(f"{result['message']}\n")

    # Run interactive in agentic mode
    pipeline.interactive(agentic=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        test_interactive_agentic()
    else:
        test_agentic_vs_standard()
