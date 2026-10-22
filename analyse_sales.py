from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_DIR / "outputs" / "cleaned" / "sales.csv"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "analysis"
DATABASE_FILE = OUTPUT_DIR / "retail.db"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT_FILE.exists():
    raise FileNotFoundError("Run clean_data.py before running this script.")

print("Reading cleaned sales...")

# Keep identifiers as text, even when they contain only numbers.
df = pd.read_csv(
    INPUT_FILE,
    dtype={
        "InvoiceNo": "string",
        "StockCode": "string",
        "CustomerID": "string",
    },
)

# Select and rename columns for easier SQL queries.
sales = df[
    [
        "source_excel_row",
        "InvoiceNo",
        "StockCode",
        "Description",
        "InvoiceDate",
        "Quantity",
        "CustomerID",
        "Country",
        "line_amount_gbp",
    ]
].rename(
    columns={
        "InvoiceNo": "invoice_no",
        "StockCode": "stock_code",
        "Description": "description",
        "InvoiceDate": "invoice_date",
        "Quantity": "quantity",
        "CustomerID": "customer_id",
        "Country": "country",
        "line_amount_gbp": "line_amount",
    }
)

# SQLite date functions expect a consistent date format.
sales["invoice_date"] = pd.to_datetime(
    sales["invoice_date"], errors="raise"
).dt.strftime("%Y-%m-%d %H:%M:%S")

queries = {
    "monthly_sales": """
        SELECT
            strftime('%Y-%m', invoice_date) AS month,
            COUNT(DISTINCT invoice_no) AS order_count,
            SUM(quantity) AS units_sold,
            ROUND(SUM(line_amount), 2) AS sales_amount_gbp
        FROM sales
        GROUP BY strftime('%Y-%m', invoice_date)
        ORDER BY month
    """,

    "top_products": """
        SELECT
            stock_code,
            SUM(quantity) AS units_sold,
            COUNT(DISTINCT invoice_no) AS order_count,
            ROUND(SUM(line_amount), 2) AS sales_amount_gbp
        FROM sales
        GROUP BY stock_code
        ORDER BY sales_amount_gbp DESC, stock_code
        LIMIT 10
    """,

    "sales_by_country": """
        SELECT
            country,
            COUNT(DISTINCT invoice_no) AS order_count,
            ROUND(SUM(line_amount), 2) AS sales_amount_gbp
        FROM sales
        GROUP BY country
        ORDER BY sales_amount_gbp DESC, country
    """,
}

with sqlite3.connect(DATABASE_FILE) as connection:
    print("Saving to SQLite...")

    # Replace this derived table when rerunning the script.
    sales.to_sql(
        "sales",
        connection,
        if_exists="replace",
        index=False,
        chunksize=10000,
    )

    # Confirm that every input row reached the database.
    stored_rows = connection.execute(
        "SELECT COUNT(*) FROM sales"
    ).fetchone()[0]

    assert stored_rows == len(sales), "Database row count mismatch."
    print(f"Rows stored: {stored_rows:,}")

    for name, query in queries.items():
        result = pd.read_sql_query(query, connection)

        # The final month in this dataset is incomplete.
        if name == "monthly_sales":
            result["coverage_note"] = ""
            result.loc[
                result["month"].eq("2011-12"), "coverage_note"
            ] = "Partial month: source data ends on 2011-12-09"

        result.to_csv(
            OUTPUT_DIR / f"{name}.csv",
            index=False,
            encoding="utf-8-sig",
        )

        # Save the SQL so it can be reviewed independently.
        (OUTPUT_DIR / f"{name}.sql").write_text(
            query.strip() + ";\n",
            encoding="utf-8",
        )

        print(f"\n{name}")
        print(result.head(10).to_string(index=False))

print(f"\nFinished. Results saved to: {OUTPUT_DIR}")