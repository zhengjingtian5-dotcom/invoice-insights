# Validation record

## Dashboard checks observed on Windows

- All categories, December 2010–December 2011: positive GBP 10,642,110.80;
  cancellations GBP 893,979.73; signed balance GBP 9,748,131.07.
- Postage only, full period: GBP 284,350.65 / 11,874.53 / 272,476.12.
- Postage only, December 2010–November 2011: GBP 261,712.67 /
  11,834.03 / 249,878.64. The incomplete-month warning disappears.
- The downloaded CSV contains 12 monthly rows. Each row reconciles, and the
  sums match the postage-only dashboard cards for that period.
- Selecting Other codes displays a descending top-10 signed-balance ranking.

These are observed checks, not a comprehensive automated test suite.
The source data and derived database are not bundled with this repository.

## Reproduction checks

On 22 October 2026, the uploaded `clean_data.py` and
`analyse_transactions.py` were rerun against the original workbook using
pandas 2.2.3 and openpyxl 3.1.5. All script assertions passed; the classification
counts, 534,129 accepted rows, overall totals and zero balance for code 23843
matched the README. All seven Python files also passed syntax parsing.
The Streamlit server was not rerun in this review environment; UI observations
above come from the Windows screenshots and exported CSV.

Run `clean_data.py`, then `analyse_transactions.py` against the original UCI
workbook. Expected counts and totals are listed in the README. The scripts
assert the row-count reconciliation, accepted amount signs, unique source-row
references, SQLite row count, and zero signed balance for code 23843.

## Remaining limitations

- Only DOT, POST and M have explicit category assignments.
- Cancellations are aggregated by their recorded dates; this is not a complete
  order-to-cancellation matching system.
- Amounts use floating-point arithmetic, with reports rounded to two decimals.
- Streamlit is not version-pinned; the exact version installed on the Windows
  development machine was not supplied.
- There is no public deployment or authentication layer.
