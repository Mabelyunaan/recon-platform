"""
Reconciliation: outer-join the two datasets on the user-chosen key and
compare the user-chosen columns, producing one status per key.
"""
import pandas as pd
import numpy as np


def _values_equal(a, b) -> bool:
    """NaN == NaN counts as equal (both missing is not a mismatch)."""
    if pd.isna(a) and pd.isna(b):
        return True
    return a == b


def reconcile(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    key_col_a: str,
    key_col_b: str,
    compare_pairs: list,
    file_a_label: str,
    file_b_label: str,
) -> pd.DataFrame:
    """
    compare_pairs: list of dicts {"alias": ..., "col_a": ..., "col_b": ...}

    Returns a DataFrame with columns:
        key, status, mismatch_columns,
        <alias>_<file_a_label>, <alias>_<file_b_label> for each compared column
    """
    a = df_a.copy()
    b = df_b.copy()

    # Rename the key columns to a common name for the merge
    a = a.rename(columns={key_col_a: "_key"})
    b = b.rename(columns={key_col_b: "_key"})

    # Keep only the key + compared columns from each side to keep this focused
    a_cols = ["_key"] + [p["col_a"] for p in compare_pairs]
    b_cols = ["_key"] + [p["col_b"] for p in compare_pairs]
    a_small = a[a_cols].add_suffix(f"__{file_a_label}")
    a_small = a_small.rename(columns={f"_key__{file_a_label}": "_key"})
    b_small = b[b_cols].add_suffix(f"__{file_b_label}")
    b_small = b_small.rename(columns={f"_key__{file_b_label}": "_key"})

    merged = pd.merge(
        a_small, b_small, on="_key", how="outer", indicator=True
    )

    statuses = []
    mismatch_cols_list = []

    for _, row in merged.iterrows():
        indicator = row["_merge"]
        if indicator == "left_only":
            statuses.append(f"MISSING_FROM_{file_b_label.upper()}")
            mismatch_cols_list.append(None)
            continue
        if indicator == "right_only":
            statuses.append(f"MISSING_FROM_{file_a_label.upper()}")
            mismatch_cols_list.append(None)
            continue

        # present in both -> compare each column
        mismatched = []
        for pair in compare_pairs:
            col_a_name = f"{pair['col_a']}__{file_a_label}"
            col_b_name = f"{pair['col_b']}__{file_b_label}"
            if not _values_equal(row[col_a_name], row[col_b_name]):
                mismatched.append(pair["alias"])

        if mismatched:
            statuses.append("MISMATCH")
            mismatch_cols_list.append(", ".join(mismatched))
        else:
            statuses.append("MATCH")
            mismatch_cols_list.append(None)

    merged["status"] = statuses
    merged["mismatch_columns"] = mismatch_cols_list
    merged = merged.drop(columns=["_merge"])
    merged = merged.rename(columns={"_key": "key"})

    # Put status columns right after the key for readability
    ordered_cols = ["key", "status", "mismatch_columns"] + [
        c for c in merged.columns if c not in ("key", "status", "mismatch_columns")
    ]
    return merged[ordered_cols]


def summarize(results_df: pd.DataFrame) -> pd.Series:
    return results_df["status"].value_counts()
