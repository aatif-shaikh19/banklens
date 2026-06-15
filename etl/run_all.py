"""
etl/run_all.py
Master ETL runner — runs all three loaders in sequence.
Order: campaigns (fast, tests BigQuery) -> fdic (tests Snowflake) -> transactions (large)
Usage: python etl\run_all.py
"""
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

DIVIDER = "=" * 60


def run() -> None:
    from etl.load_campaigns    import run as load_campaigns
    from etl.load_fdic         import run as load_fdic
    from etl.load_transactions import run as load_transactions

    steps = [
        ("Campaign data (UCI Bank Marketing -> BigQuery)",  load_campaigns),
        ("Regulatory data (FDIC cache -> Snowflake)",       load_fdic),
        ("Transaction data (IEEE-CIS -> BigQuery, ~5 min)", load_transactions),
    ]

    results = []
    for name, fn in steps:
        logger.info(f"\n{DIVIDER}")
        logger.info(f"Starting: {name}")
        logger.info(DIVIDER)
        start = time.time()
        try:
            fn()
            elapsed = round(time.time() - start, 1)
            results.append((name, "PASSED", elapsed))
        except Exception as exc:
            elapsed = round(time.time() - start, 1)
            results.append((name, f"FAILED: {exc}", elapsed))
            logger.error(f"FAILED: {exc}")

    logger.info(f"\n{DIVIDER}")
    logger.info("ETL SUMMARY")
    logger.info(DIVIDER)
    all_passed = True
    for name, status, elapsed in results:
        icon = "PASSED" if "PASSED" in status else "FAILED"
        logger.info(f"[{icon}]  {elapsed:>6.1f}s | {name}")
        if "FAILED" in status:
            logger.error(f"  Error: {status}")
            all_passed = False

    if not all_passed:
        raise SystemExit("\nOne or more ETL steps failed. Check logs above.")
    logger.info("\nAll 3 datasets loaded successfully!")


if __name__ == "__main__":
    run()
