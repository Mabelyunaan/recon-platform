"""
Transformation: standardize types of the columns that will actually be
compared, so a mismatch isn't just "5" (string) vs 5 (int). Uses
errors="coerce" so bad values become NaN/NaT rather than crashing --
validation is responsible for catching those, not transformation.
"""
import pandas as pd
import warnings


def infer_column_type(series_a: pd.Series, series_b: pd.Series) -> str:
    """
    Looks at both files' version of a column together and decides whether it
    should be treated as numeric, datetime, or left as a string.
    """
    combined = pd.concat([series_a.dropna(), series_b.dropna()])
    if len(combined) == 0:
        return "string"

    numeric_ratio = pd.to_numeric(combined, errors="coerce").notna().mean()
    if numeric_ratio >= 0.8:
        return "numeric"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        datetime_ratio = pd.to_datetime(combined, errors="coerce").notna().mean()
    if datetime_ratio >= 0.8:
        return "datetime"

    return "string"


def coerce_column(series: pd.Series, dtype: str) -> pd.Series:
    if dtype == "numeric":
        return pd.to_numeric(series, errors="coerce")
    if dtype == "datetime":
        return pd.to_datetime(series, errors="coerce")
    return series.astype("string")


def standardize_columns(df_a: pd.DataFrame, df_b: pd.DataFrame, column_pairs: list) -> tuple:
    """
    column_pairs: list of dicts like {"alias": "quantity", "col_a": "qty", "col_b": "quantity"}
    Returns (df_a_out, df_b_out, type_map) where df_a_out/df_b_out have the
    compared columns coerced to consistent types, and type_map records what
    type each alias was resolved to.
    """
    df_a_out = df_a.copy()
    df_b_out = df_b.copy()
    type_map = {}

    for pair in column_pairs:
        alias, col_a, col_b = pair["alias"], pair["col_a"], pair["col_b"]
        dtype = infer_column_type(df_a[col_a], df_b[col_b])
        type_map[alias] = dtype
        df_a_out[col_a] = coerce_column(df_a[col_a], dtype)
        df_b_out[col_b] = coerce_column(df_b[col_b], dtype)

    return df_a_out, df_b_out, type_map
