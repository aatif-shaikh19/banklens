"""
great_expectations/checkpoints/campaigns_checkpoint.py
Data quality gate for banklens_raw.campaigns.
Uses Great Expectations 1.x Fluent API (ephemeral mode).
Run: python great_expectations/checkpoints/campaigns_checkpoint.py
"""
import sys
import os
import pandas as pd
import great_expectations as gx
from dotenv import load_dotenv

load_dotenv()


def run() -> bool:
    sample_path = os.path.join("data", "sample", "sample_bank-additional-full.csv")
    if not os.path.exists(sample_path):
        print(f"Sample file not found: {sample_path}")
        print("Run: python scripts\\create_samples.py")
        sys.exit(1)

    print("Loading sample campaign data for GE validation...")
    df = pd.read_csv(sample_path)
    print(f"Loaded {len(df):,} rows x {df.shape[1]} columns")

    context = gx.get_context(mode="ephemeral")

    data_source = context.data_sources.add_pandas("campaigns_pandas_source")
    data_asset  = data_source.add_dataframe_asset("campaigns_dataframe_asset")
    batch_def   = data_asset.add_batch_definition_whole_dataframe(
        "campaigns_full_batch"
    )

    suite = context.suites.add(
        gx.ExpectationSuite(name="campaigns_quality_suite")
    )

    # Target column must only contain yes/no
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="y")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="y", value_set=["yes", "no"]
        )
    )

    # Proportion of unique values in y — should be exactly 2 (yes and no)
    suite.add_expectation(
        gx.expectations.ExpectColumnProportionOfUniqueValuesToBeBetween(
            column="y", min_value=0.0, max_value=1.0
        )
    )

    # Contact channel must be cellular or telephone
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="contact",
            value_set=["cellular", "telephone"],
        )
    )

    # Age must be in reasonable range
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="age", min_value=17, max_value=100
        )
    )

    # No nulls on key columns
    for col in ["age", "job", "contact", "y"]:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
        )

    validation_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="campaigns_validation",
            data=batch_def,
            suite=suite,
        )
    )

    print("\nRunning Great Expectations validation...")
    result = validation_def.run(batch_parameters={"dataframe": df})

    total  = len(result.results)
    passed = sum(1 for r in result.results if r.success)
    failed = total - passed

    print(f"\n{'='*55}")
    print(f"GE Validation Results -- campaigns")
    print(f"{'='*55}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"Overall: {result.success}")
    print(f"{'='*55}")

    if not result.success:
        for r in result.results:
            if not r.success:
                print(f"  FAILED  {r.expectation_config.type}: {r.result}")
        raise RuntimeError(
            f"campaigns checkpoint FAILED: {failed} expectation(s) failed"
        )

    print(f"\nAll {total} expectations passed")
    return True


if __name__ == "__main__":
    run()
