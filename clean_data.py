from pathlib import Path

import pandas as pd


# Locate files relative to this script.
PROJECT_DIR = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_DIR / "data" / "Online Retail.xlsx"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Reading Excel...")

df = pd.read_excel(INPUT_FILE, engine="openpyxl")
original_columns = df.columns.tolist()

# Check duplicates before adding row numbers or converting values.
duplicate = df.duplicated(subset=original_columns, keep="first")

# Keep the source row number for traceability.
df.insert(0, "source_excel_row", range(2, len(df) + 2))

# Create working values without overwriting the original columns.
invoice = df["InvoiceNo"].astype("string").str.strip()
date = pd.to_datetime(df["InvoiceDate"], errors="coerce")
quantity = pd.to_numeric(df["Quantity"], errors="coerce")
price = pd.to_numeric(df["UnitPrice"], errors="coerce")

is_cancellation = invoice.str.upper().str.startswith("C", na=False)

# Store all applicable review reasons.
df["review_reason"] = ""

review_checks = {
    "missing_invoice": invoice.isna() | invoice.eq("").fillna(False),
    "invalid_date": date.isna(),
    "invalid_quantity": quantity.isna() | quantity.isin([float("inf"), float("-inf")]),
    "invalid_price": price.isna() | price.isin([float("inf"), float("-inf")]),
    "zero_quantity": quantity.eq(0),
    "zero_or_negative_price": price.le(0),
    "negative_quantity_without_cancellation": quantity.lt(0) & ~is_cancellation,
    "cancellation_without_negative_quantity": is_cancellation & quantity.ge(0),
}

for reason, mask in review_checks.items():
    df.loc[mask, "review_reason"] += reason + "; "

df["review_reason"] = df["review_reason"].str.rstrip("; ")

# Assign exactly one destination to every original row.
# Priority: duplicate > review > cancellation > sale.
df["status"] = "sale"
df.loc[is_cancellation, "status"] = "cancellation"
df.loc[df["review_reason"].ne(""), "status"] = "review"
df.loc[duplicate, "status"] = "duplicate"

# Keep missing customer IDs; do not invent customer information.
df["customer_missing"] = df["CustomerID"].isna()
df["description_missing"] = df["Description"].isna()

# Only calculate amounts for rows accepted into analysis.
accepted = df["status"].isin(["sale", "cancellation"])
df["line_amount_gbp"] = (quantity * price).where(accepted)

# Export separate datasets.
file_names = {
    "sale": "sales.csv",
    "cancellation": "cancellations.csv",
    "review": "needs_review.csv",
    "duplicate": "duplicates.csv",
}

for status, file_name in file_names.items():
    subset = df.loc[df["status"].eq(status)]
    subset.to_csv(OUTPUT_DIR / file_name, index=False, encoding="utf-8-sig")

# Save a count reconciliation.
counts = df["status"].value_counts().reindex(file_names, fill_value=0)
summary = counts.rename_axis("status").reset_index(name="row_count")

assert int(summary["row_count"].sum()) == len(df)

summary.to_csv(OUTPUT_DIR / "cleaning_summary.csv", index=False)

print("\nFinished. Original Excel unchanged.")
print(summary.to_string(index=False))
print(f"\nTotal input rows: {len(df):,}")
print(f"Output folder: {OUTPUT_DIR}")