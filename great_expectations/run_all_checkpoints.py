"""
great_expectations/run_all_checkpoints.py
Runs all GE checkpoints in sequence.
Used by: GitHub Actions weekly pipeline, manual quality checks.
Run from repo root: python great_expectations\run_all_checkpoints.py
"""
import sys
import os
import time

# Add the checkpoints/ subdirectory to sys.path so we can import the scripts
# directly. We do NOT add great_expectations/ itself (that would shadow the
# installed great_expectations PyPI package used inside each checkpoint).
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "checkpoints"))

from transactions_checkpoint import run as check_transactions
from campaigns_checkpoint import run as check_campaigns


def run():
    checkpoints = [
        ("transactions", check_transactions),
        ("campaigns",    check_campaigns),
    ]

    results = []
    for name, fn in checkpoints:
        print(f"\n{'─'*55}")
        print(f"Running checkpoint: {name}")
        print(f"{'─'*55}")
        start = time.time()
        try:
            fn()
            elapsed = round(time.time() - start, 1)
            results.append((name, True, elapsed))
        except Exception as exc:
            elapsed = round(time.time() - start, 1)
            results.append((name, False, elapsed))
            print(f"ERROR: {exc}")

    print(f"\n{'='*55}")
    print("CHECKPOINT SUMMARY")
    print(f"{'='*55}")
    all_passed = True
    for name, passed, elapsed in results:
        icon = "PASSED" if passed else "FAILED"
        print(f"[{icon}]  {elapsed:>5.1f}s  {name}")
        if not passed:
            all_passed = False

    if not all_passed:
        print("\nOne or more checkpoints failed -- fix data quality issues before proceeding")
        sys.exit(1)

    print("\nAll checkpoints passed -- data is production-ready")


if __name__ == "__main__":
    run()
