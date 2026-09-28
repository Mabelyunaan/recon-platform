"""
Validation: generic data-quality checks run on a single file, driven by
whichever key/compare columns the user has selected. Does not know anything
about "orders" or "fulfillment" specifically.
"""
import pandas as pd


def run_data_quality_checks(df: pd.DataFrame, key_column: str, compare_columns: list, file_label: str) -> list:
    """
    Returns a list of check-result dicts:
        {
            "check_name": str,
            "passed": bool,
            "affected_row_count": int,
            "detail": str,
        }
    """
    results = []
    required_columns = [key_column] + compare_columns

    # 1. Required columns present
    missing_cols = [c for c in required_columns if c not in df.columns]
    results.append({
        "check_name": "required_columns_present",
        "passed": len(missing_cols) == 0,
        "affected_row_count": 0,
        "detail": f"Missing columns: {missing_cols}" if missing_cols else "All required columns present.",
    })
    if missing_cols:
        # Can't safely run the rest of the checks without the columns
        results.append({
            "check_name": "further_checks_skipped",
            "passed": False,
            "affected_row_count": len(df),
            "detail": "Skipped remaining checks because required columns are missing.",
        })
        return results

    # 2. Duplicate keys
    dup_mask = df[key_column].duplicated(keep=False)
    dup_count = int(dup_mask.sum())
    results.append({
        "check_name": "duplicate_keys",
        "passed": dup_count == 0,
        "affected_row_count": dup_count,
        "detail": f"{dup_count} row(s) share a duplicate '{key_column}' value." if dup_count else "No duplicate keys.",
    })

    # 3. Missing values in key column
    key_na_count = int(df[key_column].isna().sum())
    results.append({
        "check_name": "missing_key_values",
        "passed": key_na_count == 0,
        "affected_row_count": key_na_count,
        "detail": f"{key_na_count} row(s) missing a value in '{key_column}'." if key_na_count else "No missing keys.",
    })

    # 4. Missing values in compare columns
    for col in compare_columns:
        na_count = int(df[col].isna().sum())
        results.append({
            "check_name": f"missing_values_{col}",
            "passed": na_count == 0,
            "affected_row_count": na_count,
            "detail": f"{na_count} row(s) missing a value in '{col}'." if na_count else f"No missing values in '{col}'.",
        })

    # 5. Type consistency for compare columns that look numeric
    for col in compare_columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        coerced = pd.to_numeric(non_null, errors="coerce")
        looks_numeric_ratio = coerced.notna().mean()
        # Only flag as a "numeric consistency" issue if most values in the
        # column ARE numeric but a few aren't (i.e. it's meant to be numeric).
        if looks_numeric_ratio >= 0.7:
            bad_count = int(coerced.isna().sum())
            results.append({
                "check_name": f"numeric_consistency_{col}",
                "passed": bad_count == 0,
                "affected_row_count": bad_count,
                "detail": (
                    f"{bad_count} non-numeric value(s) found in what looks like a numeric column '{col}'."
                    if bad_count else f"'{col}' is consistently numeric."
                ),
            })

    return results


def all_checks_passed(dq_results: list) -> bool:
    return all(r["passed"] for r in dq_results)
