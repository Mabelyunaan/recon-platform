# Data Reconciliation Platform

A Streamlit app that lets you upload any two CSV files, define how they
should be matched and compared, run data-quality checks on each independently,
then reconcile them and track results over time.

Implements the design in `reconciliation-platform-design.md`.

## Project structure

```
recon_platform/
├── app.py                     # Streamlit UI (entry point)
├── requirements.txt
├── src/
│   ├── ingestion.py            # reads uploaded CSVs
│   ├── validation.py           # generic per-file data quality checks
│   ├── transformation.py       # type standardization across both files
│   ├── reconciliation.py       # outer join + comparison logic
│   └── persistence.py          # SQLite storage (runs, DQ results, results)
└── sample_data/
    ├── generate_sample_data.py # creates two sample CSVs to test with
    ├── orders_sample.csv
    └── fulfillment_sample.csv
```

## 1. Setup

Requires Python 3.9+.

```bash
cd recon_platform
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 2. Run the app

```bash
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`.
A local SQLite file `recon_platform.db` is created automatically in the
project folder on first run — this is where all run history lives.

## 3. Try it with the sample data

Two sample files are included (deliberately with **different column names**
on each side, to prove the mapping logic works generically):

- `sample_data/orders_sample.csv` — columns: `order_id`, `qty`, `order_status`
- `sample_data/fulfillment_sample.csv` — columns: `ref_id`, `quantity`, `fulfillment_status`

To regenerate them (optional, they're already included):
```bash
python sample_data/generate_sample_data.py
```

In the app:
1. Go to the **Run Reconciliation** tab.
2. Upload `orders_sample.csv` as File A and `fulfillment_sample.csv` as File B.
3. Set the key column: File A → `order_id`, File B → `ref_id`.
4. Add comparison columns:
   - Label `quantity` → File A `qty`, File B `quantity`
   - Label `status` → File A `order_status`, File B `fulfillment_status`
5. Click **Run Data Quality Check + Reconciliation**.

You should see:
- A data quality report flagging a duplicate key and a non-numeric quantity
  value in File A.
- A reconciliation summary with `MATCH`, `MISMATCH`, `MISSING_FROM_A`, and
  `MISSING_FROM_B` counts.
- The full results table, downloadable as CSV.

Go to the **History & Trends** tab afterward to see the run logged, with a
trend chart (run this a few times with different files/data to see it build
up).

## 4. Using your own files

Any two CSVs work — they don't need matching column names or the same
schema. Just:
1. Upload both.
2. Pick which column is the join key in each.
3. Add one comparison pair per field you want reconciled, with a label of
   your choice (the label is what shows up in the results/mismatch report).

## Notes / current limitations

- CSV only for now (Excel support would be a small addition to `ingestion.py`).
- Column type (numeric / datetime / string) is auto-inferred by looking at
  both files' values together — no manual override yet.
- No authentication — this is a single-user local tool as built. For a
  shared/hosted deployment, add auth and consider moving `persistence.py`
  from SQLite to a proper server-based database (e.g. Postgres).
- `mismatch_columns` currently stores a single comma-separated string. This
  matches the "generic MISMATCH + detail" option from the open questions in
  the design doc; switching to per-column mismatch statuses would mean
  changing the status logic in `reconciliation.py`.
