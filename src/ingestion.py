"""
Ingestion: read an uploaded file into a pandas DataFrame.
"""
import pandas as pd
import io


def load_file(uploaded_file) -> pd.DataFrame:
    """
    Reads an uploaded file (Streamlit UploadedFile, or a path/buffer) into a
    DataFrame. Currently supports CSV; raises a clear error otherwise.
    """
    name = getattr(uploaded_file, "name", str(uploaded_file))

    if name.lower().endswith(".csv"):
        # Reset pointer in case it was read before (Streamlit reruns)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)
    else:
        raise ValueError(
            f"Unsupported file type for '{name}'. Only .csv is supported in this version."
        )

    if df.empty:
        raise ValueError(f"'{name}' loaded but contains no rows.")

    return df
