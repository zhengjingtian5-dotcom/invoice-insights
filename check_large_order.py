from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "outputs" / "cleaned"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "investigation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

columns = [
    "source_excel_row",
    "InvoiceNo",
    "StockCode",
    "Description",
    "InvoiceDate",
    "CustomerID",
    "Quantity",
    "UnitPrice",
    "line_amount_gbp",
]

records = []

for filename in ["sales.csv", "cancellations.csv"]:
    df = pd.read_csv(
        DATA_DIR / filename,
        dtype={
            "InvoiceNo": "string",
            "StockCode": "string",
            "CustomerID": "string",
        },
    )

    # Select all records for this product.
    selected = df.loc[
        df["StockCode"].str.strip().eq("23843"), columns
    ].copy()

    selected.insert(0, "record_type", filename.removesuffix(".csv"))
    records.append(selected)

result = pd.concat(records, ignore_index=True)
result["InvoiceDate"] = pd.to_datetime(result["InvoiceDate"])
result = result.sort_values(["InvoiceDate", "source_excel_row"])

print("\nAll accepted sales and cancellations for product 23843:")
print(result.to_string(index=False))

summary = result.groupby("record_type").agg(
    line_count=("InvoiceNo", "size"),
    total_quantity=("Quantity", "sum"),
    total_amount_gbp=("line_amount_gbp", "sum"),
)

print("\nSummary:")
print(summary.round(2).to_string())

print(
    "\nCombined signed amount (GBP):",
    round(result["line_amount_gbp"].sum(), 2),
)

result.to_csv(
    OUTPUT_DIR / "product_23843_records.csv",
    index=False,
    encoding="utf-8-sig",
)

print("\nFinished.")