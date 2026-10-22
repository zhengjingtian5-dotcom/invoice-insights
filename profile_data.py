"""Inspect the original workbook without deleting or changing its records."""
import argparse
import json
from pathlib import Path

import pandas as pd


def profile_data(input_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook = pd.ExcelFile(input_path, engine="openpyxl")
    df = pd.read_excel(workbook, sheet_name=0)
    required = {"InvoiceNo", "StockCode", "Description", "Quantity",
                "InvoiceDate", "UnitPrice", "CustomerID", "Country"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # String conversion is for checks only; the original dataframe stays intact.
    invoice = df["InvoiceNo"].astype("string")
    dates = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    quantity = pd.to_numeric(df["Quantity"], errors="coerce")
    price = pd.to_numeric(df["UnitPrice"], errors="coerce")
    cancelled = invoice.str.upper().str.startswith("C", na=False)
    extra_duplicates = df.duplicated(keep="first")
    duplicate_group = df.duplicated(keep=False)

    columns = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "missing_percent": [round(df[c].isna().mean() * 100, 4) for c in df.columns],
        "unique_non_missing": [int(df[c].nunique()) for c in df.columns],
    })
    checks = {
        "exact_duplicate_after_first": extra_duplicates,
        "cancellation_invoice": cancelled,
        "negative_quantity": quantity.lt(0),
        "zero_quantity": quantity.eq(0),
        "negative_price": price.lt(0),
        "zero_price": price.eq(0),
        "missing_customer": df["CustomerID"].isna(),
        "missing_description": df["Description"].isna(),
        "missing_or_invalid_date": dates.isna(),
        "missing_or_invalid_quantity": quantity.isna(),
        "missing_or_invalid_price": price.isna(),
        "negative_quantity_without_cancellation": quantity.lt(0) & ~cancelled,
    }
    summary = {
        "input_file": input_path.name,
        "sheet_names": workbook.sheet_names,
        "analysed_sheet": workbook.sheet_names[0],
        "rows": len(df), "columns": len(df.columns),
        "date_min": str(dates.min()), "date_max": str(dates.max()),
        "unique_invoices_including_cancellations": int(invoice.nunique()),
        "unique_customers_non_missing": int(df["CustomerID"].nunique()),
        "unique_countries": int(df["Country"].nunique()),
        "rows_in_exact_duplicate_groups": int(duplicate_group.sum()),
        "checks": {name: int(mask.sum()) for name, mask in checks.items()},
        "missing_by_column": dict(zip(columns.column, columns.missing_count)),
        "note": "Flags overlap and are not automatic deletion rules. No records removed.",
    }
    columns.to_csv(output_dir / "column_profile.csv", index=False)
    df.head(20).to_csv(output_dir / "first_20_rows.csv", index=False)
    examples = []
    for name, mask in checks.items():
        sample = df.loc[mask].head(5).copy()
        sample.insert(0, "excel_row", sample.index + 2)
        sample.insert(0, "check", name)
        examples.append(sample)
    pd.concat(examples, ignore_index=True).to_csv(
        output_dir / "issue_examples.csv", index=False)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    workbook.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to Online Retail.xlsx")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    profile_data(args.input, args.output)
