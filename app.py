from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Invoice Insights", layout="wide")

PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_DIR / "outputs" / "analysis_v2" / "retail_v2.db"

st.title("Invoice Insights")
st.caption("Historical retail transactions · All amounts in GBP")

if not DATABASE_FILE.exists():
    st.error("Database missing. Run analyse_transactions.py first.")
    st.stop()


def query(sql, params=()):
    """Read from SQLite without changing the database."""
    uri = DATABASE_FILE.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        return pd.read_sql_query(sql, connection, params=params)


months = query("""
    SELECT DISTINCT substr(invoice_date, 1, 7) AS month
    FROM transactions
    ORDER BY month
""")["month"].tolist()

if not months:
    st.error("The database contains no transactions.")
    st.stop()

category_labels = {
    "other_codes": "Other codes — not fully classified",
    "postage": "Postage — DOT / POST",
    "manual": "Manual — M",
}

# Sidebar controls
st.sidebar.header("Filters")

start_month = st.sidebar.selectbox("Start month", months, index=0)
end_month = st.sidebar.selectbox(
    "End month", months, index=len(months) - 1
)

categories = st.sidebar.multiselect(
    "Categories",
    options=list(category_labels),
    default=list(category_labels),
    format_func=lambda value: category_labels[value],
)

if start_month > end_month:
    st.warning("Start month must be before or equal to end month.")
    st.stop()

if not categories:
    st.info("Select at least one category.")
    st.stop()

# Only placeholder syntax is constructed here.
# Selected values are passed separately as SQL parameters.
placeholders = ", ".join("?" for _ in categories)

where_clause = f"""
    WHERE substr(invoice_date, 1, 7) BETWEEN ? AND ?
      AND category IN ({placeholders})
"""

params = (start_month, end_month, *categories)

metrics_sql = """
    SUM(CASE WHEN transaction_type = 'sale'
        THEN line_amount ELSE 0 END) AS positive_sales_gbp,
    SUM(CASE WHEN transaction_type = 'cancellation'
        THEN -line_amount ELSE 0 END) AS cancellation_amount_gbp,
    SUM(line_amount) AS signed_balance_gbp
"""

metric_labels = {
    "positive_sales_gbp": "Positive sales",
    "cancellation_amount_gbp": "Cancellations",
    "signed_balance_gbp": "Signed balance",
}

st.caption(f"Selected period: {start_month} to {end_month}")

if start_month <= "2011-12" <= end_month:
    st.warning(
        "December 2011 is incomplete: source data ends on 9 December. "
        "Do not compare it directly with a full month."
    )

totals = query(
    f"SELECT {metrics_sql} FROM transactions {where_clause}",
    params,
).fillna(0).iloc[0]

cards = st.columns(3)
for card, (field, label) in zip(cards, metric_labels.items()):
    card.metric(label, f"£{totals[field]:,.2f}")

st.caption(
    "Signed balance = positive sales − cancellations. "
    "It is not profit or cash collected."
)

# Monthly trend, using the same filters as the metric cards.
monthly = query(
    f"""
    SELECT substr(invoice_date, 1, 7) AS month, {metrics_sql}
    FROM transactions
    {where_clause}
    GROUP BY substr(invoice_date, 1, 7)
    ORDER BY month
    """,
    params,
)

st.subheader("Monthly amounts")
st.line_chart(
    monthly.set_index("month").rename(columns=metric_labels),
    x_label="Month",
    y_label="GBP",
)

# Category comparison
category_totals = query(
    f"""
    SELECT category, {metrics_sql}
    FROM transactions
    {where_clause}
    GROUP BY category
    ORDER BY category
    """,
    params,
)

st.subheader("Signed balance by category")
category_chart = category_totals.copy()
category_chart["category"] = category_chart["category"].map(category_labels)

st.bar_chart(
    category_chart.set_index("category")[["signed_balance_gbp"]]
    .rename(columns={"signed_balance_gbp": "Signed balance"}),
    y_label="GBP",
)

# Recalculate the ranking for the selected period.
st.subheader("Top 10 other codes by signed balance")
st.caption(
    "Excludes DOT, POST and M. Remaining codes are not all verified "
    "as merchandise. Ranking uses the selected months."
)

if "other_codes" in categories:
    ranking = query(
        f"""
        SELECT stock_code, {metrics_sql}
        FROM transactions
        {where_clause}
          AND category = 'other_codes'
        GROUP BY stock_code
        ORDER BY signed_balance_gbp DESC, stock_code
        LIMIT 10
        """,
        params,
    )

    st.dataframe(
        ranking.rename(columns=metric_labels).round(2),
        hide_index=True,
    )
else:
    st.info("Select 'Other codes' to display this ranking.")

with st.expander("Monthly data and download"):
    st.dataframe(monthly.round(2), hide_index=True)

    st.download_button(
        "Download selected monthly data",
        data=monthly.round(2).to_csv(index=False).encode("utf-8-sig"),
        file_name="selected_monthly_amounts.csv",
        mime="text/csv",
    )

with st.expander("How to interpret this dashboard"):
    st.markdown("""
- Includes accepted sales and cancellation records from the cleaning step.
- Duplicate and review records are excluded under documented project rules.
- Cancellations are counted on their recorded dates, not the original sale dates.
- Cancellation records have not all been matched to their original orders.
- DOT and POST are postage-related; M means Manual, with its exact purpose unclear.
- Figures use floating-point calculations and are displayed to two decimal places.
- Source: UCI Online Retail, Chen (2015), CC BY 4.0.
""")
    st.markdown(
        "[Dataset source](https://archive.ics.uci.edu/dataset/352/online-retail)"
    )