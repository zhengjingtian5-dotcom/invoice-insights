from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_DIR / "outputs" / "analysis" / "retail.db"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "investigation"

if not DATABASE_FILE.exists():
    raise FileNotFoundError("Run analyse_sales.py first.")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

codes = ("DOT", "POST", "M")

# Group by both code and description to reveal different uses of a code.
summary_query = """
    SELECT
        stock_code,
        description,
        COUNT(*) AS line_count,
        COUNT(DISTINCT invoice_no) AS order_count,
        ROUND(SUM(line_amount), 2) AS positive_amount_gbp
    FROM sales
    WHERE stock_code IN (?, ?, ?)
    GROUP BY stock_code, description
    ORDER BY stock_code, positive_amount_gbp DESC
"""

# Retrieve the five largest positive lines for each code.
examples_query = """
    SELECT
        source_excel_row,
        invoice_no,
        stock_code,
        description,
        invoice_date,
        quantity,
        line_amount
    FROM sales
    WHERE stock_code = ?
    ORDER BY line_amount DESC, source_excel_row
    LIMIT 5
"""

# Read-only mode prevents accidental changes to the database.
database_uri = DATABASE_FILE.resolve().as_uri() + "?mode=ro"

with sqlite3.connect(database_uri, uri=True) as connection:
    summary = pd.read_sql_query(
        summary_query, connection, params=codes
    )

    print("\nDescriptions and amounts:")
    print(summary.to_string(index=False))

    summary.to_csv(
        OUTPUT_DIR / "special_codes_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    examples = []

    for code in codes:
        result = pd.read_sql_query(
            examples_query, connection, params=(code,)
        )

        print(f"\nLargest positive lines for {code}:")
        print(result.to_string(index=False))
        examples.append(result)

    pd.concat(examples, ignore_index=True).to_csv(
        OUTPUT_DIR / "special_codes_examples.csv",
        index=False,
        encoding="utf-8-sig",
    )

print(f"\nFinished. Results saved to: {OUTPUT_DIR}")