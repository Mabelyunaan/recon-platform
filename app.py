import streamlit as st
import pandas as pd

from src.ingestion import load_file
from src.validation import run_data_quality_checks, all_checks_passed
from src.transformation import standardize_columns
from src.reconciliation import reconcile, summarize
from src.persistence import (
    init_db, save_run, load_run_history,
    load_run_summary_counts, load_reconciliation_results, load_dq_results,
)

st.set_page_config(page_title="Data Reconciliation Platform", layout="wide")
init_db()

if "compare_pairs" not in st.session_state:
    st.session_state.compare_pairs = []

st.title("🔍 Data Reconciliation Platform")
st.caption("Upload two datasets, define how they should match, and reconcile them.")

tab_run, tab_history = st.tabs(["Run Reconciliation", "History & Trends"])


with tab_run:
    col_upload_a, col_upload_b = st.columns(2)
    with col_upload_a:
        st.subheader("File A")
        file_a = st.file_uploader("Upload File A (CSV)", type=["csv"], key="file_a")
    with col_upload_b:
        st.subheader("File B")
        file_b = st.file_uploader("Upload File B (CSV)", type=["csv"], key="file_b")

    if file_a and file_b:
        try:
            df_a = load_file(file_a)
            df_b = load_file(file_b)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        col_prev_a, col_prev_b = st.columns(2)
        with col_prev_a:
            st.write(f"**{file_a.name}** — {df_a.shape[0]} rows, {df_a.shape[1]} columns")
            st.dataframe(df_a.head(5), use_container_width=True)
        with col_prev_b:
            st.write(f"**{file_b.name}** — {df_b.shape[0]} rows, {df_b.shape[1]} columns")
            st.dataframe(df_b.head(5), use_container_width=True)

        st.divider()
        st.subheader("1. Define the key column")
        col_key_a, col_key_b = st.columns(2)
        with col_key_a:
            key_col_a = st.selectbox("Key column in File A", df_a.columns, key="key_a")
        with col_key_b:
            key_col_b = st.selectbox("Key column in File B", df_b.columns, key="key_b")

        st.subheader("2. Define columns to compare")
        st.caption("Add a pair of columns (one from each file) for every field you want reconciled, and give it a label.")

        with st.form("add_pair_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_alias = st.text_input("Label (e.g. 'quantity')")
            with c2:
                new_col_a = st.selectbox("Column in File A", df_a.columns, key="new_col_a")
            with c3:
                new_col_b = st.selectbox("Column in File B", df_b.columns, key="new_col_b")
            add_clicked = st.form_submit_button("+ Add comparison column")
            if add_clicked:
                if not new_alias.strip():
                    st.warning("Please give this comparison a label.")
                else:
                    st.session_state.compare_pairs.append(
                        {"alias": new_alias.strip(), "col_a": new_col_a, "col_b": new_col_b}
                    )

        if st.session_state.compare_pairs:
            st.write("**Columns to compare:**")
            for i, pair in enumerate(st.session_state.compare_pairs):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.write(f"`{pair['alias']}` → File A: `{pair['col_a']}`  |  File B: `{pair['col_b']}`")
                with c2:
                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.compare_pairs.pop(i)
                        st.rerun()
        else:
            st.info("No comparison columns added yet.")

        st.divider()
        run_clicked = st.button(
            "▶ Run Data Quality Check + Reconciliation",
            type="primary",
            disabled=len(st.session_state.compare_pairs) == 0,
        )

        if run_clicked:
            compare_pairs = st.session_state.compare_pairs
            compare_cols_a = [p["col_a"] for p in compare_pairs]
            compare_cols_b = [p["col_b"] for p in compare_pairs]

            # --- Validation ---
            dq_a = run_data_quality_checks(df_a, key_col_a, compare_cols_a, "File A")
            dq_b = run_data_quality_checks(df_b, key_col_b, compare_cols_b, "File B")

            st.subheader("Data Quality Report")
            col_dq_a, col_dq_b = st.columns(2)

            def render_dq(results, label, container):
                with container:
                    st.write(f"**{label}**")
                    for r in results:
                        icon = "✅" if r["passed"] else "⚠️"
                        st.write(f"{icon} **{r['check_name']}** — {r['detail']}")

            render_dq(dq_a, file_a.name, col_dq_a)
            render_dq(dq_b, file_b.name, col_dq_b)

            proceed = True
            if not (all_checks_passed(dq_a) and all_checks_passed(dq_b)):
                st.warning(
                    "One or more data quality checks failed. You can still proceed, "
                    "but treat mismatches with extra caution."
                )

            st.divider()
            st.subheader("Reconciliation Results")

            df_a_std, df_b_std, type_map = standardize_columns(df_a, df_b, compare_pairs)
            results = reconcile(
                df_a_std, df_b_std, key_col_a, key_col_b, compare_pairs,
                file_a_label="A", file_b_label="B",
            )

            summary = summarize(results)
            metric_cols = st.columns(len(summary) if len(summary) > 0 else 1)
            for i, (status, count) in enumerate(summary.items()):
                metric_cols[i].metric(status, int(count))

            status_filter = st.multiselect(
                "Filter by status", options=sorted(results["status"].unique()),
                default=[s for s in results["status"].unique() if s != "MATCH"] or list(results["status"].unique()),
            )
            filtered = results[results["status"].isin(status_filter)] if status_filter else results
            st.dataframe(filtered, use_container_width=True)

            st.download_button(
                "⬇ Download full results as CSV",
                data=results.to_csv(index=False).encode("utf-8"),
                file_name="reconciliation_results.csv",
                mime="text/csv",
            )

            run_id = save_run(
                file_a_name=file_a.name,
                file_b_name=file_b.name,
                key_column_a=key_col_a,
                key_column_b=key_col_b,
                compare_columns=[p["alias"] for p in compare_pairs],
                dq_results_a=dq_a,
                dq_results_b=dq_b,
                reconciliation_df=results,
                status="success",
            )
            st.success(f"Run saved to history (run_id: `{run_id}`).")


with tab_history:
    st.subheader("Run History")
    history = load_run_history()

    if history.empty:
        st.info("No runs yet. Go to the 'Run Reconciliation' tab to get started.")
    else:
        st.dataframe(history, use_container_width=True)

        st.subheader("Match Rate Trend")
        counts = load_run_summary_counts()
        if not counts.empty:
            pivot = counts.pivot_table(
                index="run_timestamp", columns="status", values="count", fill_value=0
            )
            st.line_chart(pivot)

        st.subheader("Inspect a specific run")
        selected_run = st.selectbox("Select run_id", history["run_id"])
        if selected_run:
            st.write("**Data quality checks for this run:**")
            st.dataframe(load_dq_results(selected_run), use_container_width=True)
            st.write("**Reconciliation results for this run:**")
            st.dataframe(
                load_reconciliation_results(selected_run)[["key_value", "status", "mismatch_columns"]],
                use_container_width=True,
            )
