"""
great_expectations/checkpoints/transactions_checkpoint.py
Data quality gate for banklens_raw.transactions.
Uses Great Expectations 1.x Fluent API (ephemeral mode — no config files needed).
Run: python great_expectations/checkpoints/transactions_checkpoint.py
"""
import sys
import os
import pandas as pd
import great_expectations as gx
from dotenv import load_dotenv

load_dotenv()


def run() -> bool:
    sample_path = os.path.join("data", "sample", "sample_train_transaction.csv")
    if not os.path.exists(sample_path):
        print(f"Sample file not found: {sample_path}")
        print("Run: python scripts\\create_samples.py")
        sys.exit(1)

    print("Loading sample transaction data for GE validation...")
    df = pd.read_csv(sample_path)
    print(f"Loaded {len(df):,} rows x {df.shape[1]} columns")

    # GE 1.x: ephemeral context — no files written, runs as a pure script
    context = gx.get_context(mode="ephemeral")

    # Step 1: Register a pandas data source
    data_source = context.data_sources.add_pandas("transactions_pandas_source")

    # Step 2: Add a DataFrame data asset
    data_asset = data_source.add_dataframe_asset("transactions_dataframe_asset")

    # Step 3: Define how to get a batch (whole DataFrame = one batch)
    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        "transactions_full_batch"
    )

    # Step 4: Create expectation suite with our rules
    suite = context.suites.add(
        gx.ExpectationSuite(name="transactions_quality_suite")
    )

    # Rule 1: TransactionID must exist and be unique
    suite.add_expectation(
        gx.expectations.ExpectColumnToExist(column="TransactionID")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="TransactionID")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="TransactionID")
    )

    # Rule 2: Amount must be positive
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="TransactionAmt")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="TransactionAmt", min_value=0.01, max_value=50000
        )
    )

    # Rule 3: Fraud label sanity — must be 0 or 1
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="isFraud")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="isFraud", value_set=[0, 1]
        )
    )

    # Rule 4: Fraud rate must be between 1% and 8% (data integrity check)
    suite.add_expectation(
        gx.expectations.ExpectColumnMeanToBeBetween(
            column="isFraud", min_value=0.01, max_value=0.08
        )
    )

    # Rule 5: ProductCD must be one of the known categories
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="ProductCD",
            value_set=["W", "C", "R", "H", "S"],
            mostly=0.95
        )
    )

    # Step 5: Create validation definition (links batch + suite)
    validation_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="transactions_validation",
            data=batch_definition,
            suite=suite,
        )
    )

    # Step 6: Run validation — pass the DataFrame as batch parameters
    print("\nRunning Great Expectations validation...")
    result = validation_def.run(
        batch_parameters={"dataframe": df}
    )

    # Step 7: Report results
    total  = len(result.results)
    passed = sum(1 for r in result.results if r.success)
    failed = total - passed

    print(f"\n{'='*55}")
    print(f"GE Validation Results -- transactions")
    print(f"{'='*55}")
    print(f"Total expectations : {total}")
    print(f"Passed             : {passed}")
    print(f"Failed             : {failed}")
    print(f"Overall success    : {result.success}")
    print(f"{'='*55}")

    if not result.success:
        print("\nFailed expectations:")
        for r in result.results:
            if not r.success:
                print(f"  FAILED  {r.expectation_config.type}")
                print(f"          {r.result}")
        raise RuntimeError(
            f"transactions checkpoint FAILED: {failed} expectation(s) did not pass"
        )

    print(f"\nAll {total} expectations passed -- data quality confirmed")
    return True


if __name__ == "__main__":
    run()
