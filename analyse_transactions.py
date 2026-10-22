from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "outputs" / "cleaned"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "analysis_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

frames = []

# Load both accepted sales and accepted cancellations.
for filename, transaction_type in [
    ("sales.csv", "sale"),
    ("cancellations.csv", "cancellation"),
]:
    df = pd.read_csv(
        INPUT_DIR / filename,
        dtype={
            "InvoiceNo": "string",
            "StockCode": "string",
            "CustomerID": "string",
        },
    )

    df["transaction_type"] = transaction_type
    frames.append(df)

transactions = pd.concat(frames, ignore_index=True)

transactions = transactions.rename(
    columns={
        "InvoiceNo": "invoice_no",
        "StockCode": "stock_code",
        "InvoiceDate": "invoice_date",
        "line_amount_gbp": "line_amount",
    }
)

transactions["stock_code"] = transactions["stock_code"].str.strip()
transactions["invoice_date"] = pd.to_datetime(
    transactions["invoice_date"], errors="raise"
).dt.strftime("%Y-%m-%d %H:%M:%S")

# Classify only the codes investigated so far.
# Other codes are not automatically verified as merchandise.
transactions["category"] = "other_codes"
transactions.loc[
    transactions["stock_code"].isin(["DOT", "POST"]), "category"
] = "postage"
transactions.loc[
    transactions["stock_code"].eq("M"), "category"
] = "manual"

# Validate signs before calculating cancellation magnitudes.
sale_mask = transactions["transaction_type"].eq("sale")
cancel_mask = transactions["transaction_type"].eq("cancellation")

assert transactions.loc[sale_mask, "line_amount"].gt(0).all()
assert transactions.loc[cancel_mask, "line_amount"].lt(0).all()
assert transactions["source_excel_row"].is_unique

# Shared SQL calculations used by every report.
metrics = """
    ROUND(SUM(
        CASE WHEN transaction_type = 'sale'
        THEN line_amount ELSE 0 END
    ), 2) AS positive_sales_gbp,

    ROUND(SUM(
        CASE WHEN transaction_type = 'cancellation'
        THEN -line_amount ELSE 0 END
    ), 2) AS cancellation_amount_gbp,

    ROUND(SUM(line_amount), 2) AS signed_balance_gbp
"""

queries = {
    "overall_totals": f"""
        SELECT {metrics}
        FROM transactions
    """,

    "monthly_by_category": f"""
        SELECT
            strftime('%Y-%m', invoice_date) AS month,
            category,
            {metrics}
        FROM transactions
        GROUP BY strftime('%Y-%m', invoice_date), category
        ORDER BY month, category
    """,

    "category_totals": f"""
        SELECT
            category,
            COUNT(*) AS line_count,
            {metrics}
        FROM transactions
        GROUP BY category
        ORDER BY category
    """,

    "top_codes_excluding_known_specials": f"""
        SELECT
            stock_code,
            {metrics}
        FROM transactions
        WHERE category = 'other_codes'
        GROUP BY stock_code
        ORDER BY signed_balance_gbp DESC, stock_code
        LIMIT 10
    """,

    "product_23843_check": f"""
        SELECT
            stock_code,
            {metrics}
        FROM transactions
        WHERE stock_code = '23843'
        GROUP BY stock_code
    """,
}

database_file = OUTPUT_DIR / "retail_v2.db"

with sqlite3.connect(database_file) as connection:
    print("Saving sales and cancellations to SQLite...")

    transactions.to_sql(
        "transactions",
        connection,
        if_exists="replace",
        index=False,
        chunksize=10000,
    )

    stored_rows = connection.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    assert stored_rows == len(transactions)
    print(f"Rows stored: {stored_rows:,}")

    for name, query in queries.items():
        result = pd.read_sql_query(query, connection)

        if name == "monthly_by_category":
            result["coverage_note"] = ""
            result.loc[
                result["month"].eq("2011-12"),
                "coverage_note",
            ] = "Partial month: source ends on 2011-12-09"

        # Confirm the investigated product offsets within this dataset.
        if name == "product_23843_check":
            assert len(result) == 1
            assert abs(result["signed_balance_gbp"].iloc[0]) < 0.01

        result.to_csv(
            OUTPUT_DIR / f"{name}.csv",
            index=False,
            encoding="utf-8-sig",
        )

        (OUTPUT_DIR / f"{name}.sql").write_text(
            query.strip() + ";\n",
            encoding="utf-8",
        )

        print(f"\n{name}")
        print(result.to_string(index=False))

print(f"\nFinished. Results saved to: {OUTPUT_DIR}")