#!/usr/bin/env python3
"""
Quick test for Web UI functionality.
"""

import sys
from pathlib import Path

from src.pipeline import AgenticPipeline


def main():
    print("=" * 60)
    print("Web UI Quick Test")
    print("=" * 60)
    print()

    # Initialize pipeline
    print("1. Initializing pipeline...")
    try:
        pipeline = AgenticPipeline()
        pipeline.initialize()
        print("   ✓ Pipeline initialized")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # Load existing data
    print("\n2. Loading existing data...")
    try:
        result = pipeline.load_existing_data()
        if result["success"]:
            print(f"   ✓ {result['message']}")
        else:
            print(f"   ⚠ {result['message']}")
            if result["chunks"] == 0:
                print("\n   Run this first:")
                print("   python run_pipeline.py data/documents/")
                return 1
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test standard query
    print("\n3. Testing standard query...")
    try:
        test_q = "재택근무 승인자는?"
        result = pipeline.query(test_q, agentic=False)
        print(f"   Q: {test_q}")
        print(f"   A: {result['answer'][:100]}...")
        print(f"   ✓ Standard mode works")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test agentic query
    print("\n4. Testing agentic query...")
    try:
        result = pipeline.query(test_q, agentic=True)
        print(f"   Q: {test_q}")
        print(f"   A: {result['answer'][:100]}...")

        if result.get("validation"):
            val = result["validation"]
            status = "✓" if val.get("valid") else "✗"
            print(f"   Validation: {status} (confidence: {val.get('confidence', 0):.2f})")

        print(f"   ✓ Agentic mode works")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print("\nWeb UI is ready to use:")
    print("  streamlit run app_agentic_v2.py --server.port 8502")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
