"""
Day 2 Data Cleaning Script for Bluestock Mutual Fund Analytics Project.

This script performs Day 2 data cleaning tasks for:
1. NAV history (02_nav_history.csv)
2. Investor transactions (08_investor_transactions.csv)
3. Scheme performance (07_scheme_performance.csv)

Outputs are written to data/processed/ and a Day 2 cleaning report is generated
at reports/day2_cleaning_report.txt.

Design goals:
- Use pathlib.Path for all file operations.
- Preserve raw data by writing cleaned outputs to processed folder.
- Log anomalies and validation outcomes for auditability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd


@dataclass
class CleaningSummary:
    """Container for per-dataset cleaning and anomaly metrics."""

    dataset_name: str
    input_rows: int
    output_rows: int
    anomalies: List[str] = field(default_factory=list)


def _print_section(title: str) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)


def clean_nav_history(raw_path: Path, processed_path: Path) -> tuple[pd.DataFrame, CleaningSummary]:
    """
    Clean 02_nav_history.csv.

    Steps:
    - Parse date to datetime.
    - Sort by amfi_code/date.
    - Remove duplicate (amfi_code, date) rows.
    - Forward-fill missing NAV only for short gaps (1-3 days), intended for
      weekend/holiday continuity.
    - Validate NAV > 0.
    """
    file_path = raw_path / "02_nav_history.csv"
    df = pd.read_csv(file_path)

    summary = CleaningSummary(
        dataset_name="02_nav_history.csv",
        input_rows=len(df),
        output_rows=0,
        anomalies=[],
    )

    required_cols = {"amfi_code", "date", "nav"}
    missing_cols = required_cols.difference(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns in nav_history: {missing_cols}")

    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="coerce").astype("Int64")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    bad_dates = int(df["date"].isna().sum())
    bad_codes = int(df["amfi_code"].isna().sum())
    if bad_dates:
        summary.anomalies.append(f"Rows with invalid date: {bad_dates}")
    if bad_codes:
        summary.anomalies.append(f"Rows with invalid amfi_code: {bad_codes}")

    df = df.dropna(subset=["amfi_code", "date"]).copy()
    df["amfi_code"] = df["amfi_code"].astype(int)

    dup_count = int(df.duplicated(subset=["amfi_code", "date"]).sum())
    if dup_count:
        summary.anomalies.append(f"Duplicate (amfi_code, date) rows removed: {dup_count}")
    df = df.sort_values(["amfi_code", "date"]).drop_duplicates(
        subset=["amfi_code", "date"], keep="last"
    )

    grouped = df.groupby("amfi_code", group_keys=False)
    df["prev_date"] = grouped["date"].shift(1)
    df["prev_nav"] = grouped["nav"].shift(1)
    df["gap_days"] = (df["date"] - df["prev_date"]).dt.days

    fill_mask = (
        df["nav"].isna()
        & df["prev_nav"].notna()
        & df["gap_days"].between(1, 3, inclusive="both")
    )
    fill_count = int(fill_mask.sum())
    if fill_count:
        summary.anomalies.append(
            f"NAV values forward-filled for short gaps (1-3 days): {fill_count}"
        )
        df.loc[fill_mask, "nav"] = df.loc[fill_mask, "prev_nav"]

    remaining_null_nav = int(df["nav"].isna().sum())
    if remaining_null_nav:
        summary.anomalies.append(f"Rows dropped due to unresolved null NAV: {remaining_null_nav}")
        df = df.dropna(subset=["nav"]).copy()

    non_positive_nav = int((df["nav"] <= 0).sum())
    if non_positive_nav:
        summary.anomalies.append(f"Rows dropped where NAV <= 0: {non_positive_nav}")
        df = df[df["nav"] > 0].copy()

    df = df[["amfi_code", "date", "nav"]].sort_values(["amfi_code", "date"]).reset_index(drop=True)

    output_file = processed_path / "02_nav_history_cleaned.csv"
    df.to_csv(output_file, index=False)

    summary.output_rows = len(df)
    return df, summary


def clean_investor_transactions(
    raw_path: Path, processed_path: Path
) -> tuple[pd.DataFrame, CleaningSummary]:
    """
    Clean 08_investor_transactions.csv.

    Steps:
    - Standardize transaction_type values to SIP/Lumpsum/Redemption.
    - Validate amount_inr > 0.
    - Fix transaction_date format.
    - Validate and standardize KYC status values.
    """
    file_path = raw_path / "08_investor_transactions.csv"
    df = pd.read_csv(file_path)

    summary = CleaningSummary(
        dataset_name="08_investor_transactions.csv",
        input_rows=len(df),
        output_rows=0,
        anomalies=[],
    )

    required_cols = {
        "investor_id",
        "transaction_date",
        "amfi_code",
        "transaction_type",
        "amount_inr",
        "kyc_status",
    }
    missing_cols = required_cols.difference(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns in investor_transactions: {missing_cols}")

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    invalid_date_rows = int(df["transaction_date"].isna().sum())
    if invalid_date_rows:
        summary.anomalies.append(f"Rows with invalid transaction_date dropped: {invalid_date_rows}")
        df = df.dropna(subset=["transaction_date"]).copy()

    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="coerce").astype("Int64")
    bad_amfi = int(df["amfi_code"].isna().sum())
    if bad_amfi:
        summary.anomalies.append(f"Rows with invalid amfi_code dropped: {bad_amfi}")
        df = df.dropna(subset=["amfi_code"]).copy()
    df["amfi_code"] = df["amfi_code"].astype(int)

    original_txn_types = df["transaction_type"].astype(str).str.strip()
    normalized_txn = original_txn_types.str.lower().str.replace("-", "", regex=False).str.replace(" ", "", regex=False)

    txn_map = {
        "sip": "SIP",
        "systematicinvestmentplan": "SIP",
        "lumpsum": "Lumpsum",
        "lumpsumpurchase": "Lumpsum",
        "onetime": "Lumpsum",
        "redemption": "Redemption",
        "redeem": "Redemption",
        "withdrawal": "Redemption",
    }
    df["transaction_type"] = normalized_txn.map(txn_map)

    unknown_txn = int(df["transaction_type"].isna().sum())
    if unknown_txn:
        summary.anomalies.append(f"Rows with unrecognized transaction_type dropped: {unknown_txn}")
        df = df.dropna(subset=["transaction_type"]).copy()

    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
    invalid_amt = int(df["amount_inr"].isna().sum())
    if invalid_amt:
        summary.anomalies.append(f"Rows with non-numeric amount dropped: {invalid_amt}")
        df = df.dropna(subset=["amount_inr"]).copy()

    non_positive_amt = int((df["amount_inr"] <= 0).sum())
    if non_positive_amt:
        summary.anomalies.append(f"Rows with amount_inr <= 0 dropped: {non_positive_amt}")
        df = df[df["amount_inr"] > 0].copy()

    kyc_normalized = df["kyc_status"].astype(str).str.strip().str.title()
    kyc_map = {
        "Verified": "Verified",
        "Pending": "Pending",
        "Rejected": "Rejected",
        "Not Verified": "Pending",
        "Unverified": "Pending",
    }
    df["kyc_status"] = kyc_normalized.map(kyc_map)

    invalid_kyc = int(df["kyc_status"].isna().sum())
    if invalid_kyc:
        summary.anomalies.append(f"Rows with invalid kyc_status dropped: {invalid_kyc}")
        df = df.dropna(subset=["kyc_status"]).copy()

    df = df.sort_values(["transaction_date", "investor_id"]).reset_index(drop=True)

    output_file = processed_path / "08_investor_transactions_cleaned.csv"
    df.to_csv(output_file, index=False)

    summary.output_rows = len(df)
    return df, summary


def clean_scheme_performance(
    raw_path: Path, processed_path: Path
) -> tuple[pd.DataFrame, CleaningSummary]:
    """
    Clean 07_scheme_performance.csv.

    Steps:
    - Ensure return/performance columns are numeric.
    - Flag anomalies (missing, extreme values).
    - Validate expense_ratio_pct is between 0.1 and 2.5.
    """
    file_path = raw_path / "07_scheme_performance.csv"
    df = pd.read_csv(file_path)

    summary = CleaningSummary(
        dataset_name="07_scheme_performance.csv",
        input_rows=len(df),
        output_rows=0,
        anomalies=[],
    )

    numeric_cols = [
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
        "morningstar_rating",
    ]

    for col in numeric_cols:
        if col not in df.columns:
            raise ValueError(f"Missing expected column in scheme_performance: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct"]:
        nulls = int(df[col].isna().sum())
        if nulls:
            summary.anomalies.append(f"Null numeric values in {col}: {nulls}")

    extreme_return_mask = (
        (df["return_1yr_pct"].abs() > 100)
        | (df["return_3yr_pct"].abs() > 100)
        | (df["return_5yr_pct"].abs() > 100)
    )
    extreme_return_count = int(extreme_return_mask.sum())
    if extreme_return_count:
        summary.anomalies.append(f"Extreme return anomalies flagged (|return| > 100): {extreme_return_count}")

    invalid_expense_mask = (df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)
    invalid_expense_count = int(invalid_expense_mask.sum())
    if invalid_expense_count:
        summary.anomalies.append(
            "Rows dropped for invalid expense_ratio_pct outside [0.1, 2.5]: "
            f"{invalid_expense_count}"
        )
        df = df[~invalid_expense_mask].copy()

    critical_cols = [
        "amfi_code",
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "expense_ratio_pct",
    ]
    missing_critical = int(df[critical_cols].isna().any(axis=1).sum())
    if missing_critical:
        summary.anomalies.append(f"Rows dropped with missing critical metrics: {missing_critical}")
        df = df.dropna(subset=critical_cols).copy()

    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="coerce").astype("Int64")
    bad_amfi = int(df["amfi_code"].isna().sum())
    if bad_amfi:
        summary.anomalies.append(f"Rows dropped with invalid amfi_code: {bad_amfi}")
        df = df.dropna(subset=["amfi_code"]).copy()
    df["amfi_code"] = df["amfi_code"].astype(int)

    output_file = processed_path / "07_scheme_performance_cleaned.csv"
    df = df.sort_values(["amfi_code", "plan"]).reset_index(drop=True)
    df.to_csv(output_file, index=False)

    summary.output_rows = len(df)
    return df, summary


def _write_cleaning_report(report_path: Path, summaries: List[CleaningSummary]) -> None:
    """Write Day 2 cleaning report for audit and quick review."""
    with report_path.open("w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DAY 2 CLEANING REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for s in summaries:
            f.write("-" * 80 + "\n")
            f.write(f"Dataset: {s.dataset_name}\n")
            f.write(f"Input rows: {s.input_rows}\n")
            f.write(f"Output rows: {s.output_rows}\n")
            f.write("Anomalies:\n")
            if s.anomalies:
                for item in s.anomalies:
                    f.write(f"  - {item}\n")
            else:
                f.write("  - None\n")
            f.write("\n")


def passthrough_remaining_datasets(
    raw_path: Path, processed_path: Path
) -> list[CleaningSummary]:
    """
    Read and save the remaining Day 2 datasets with `_cleaned.csv` suffix.

    This intentionally avoids transformation-heavy cleaning and preserves source
    values while still standardizing parseable date-like columns.
    """
    passthrough_files = [
        "01_fund_master.csv",
        "03_aum_by_fund_house.csv",
        "04_monthly_sip_inflows.csv",
        "05_category_inflows.csv",
        "06_industry_folio_count.csv",
        "09_portfolio_holdings.csv",
        "10_benchmark_indices.csv",
    ]

    summaries: list[CleaningSummary] = []

    for filename in passthrough_files:
        source_file = raw_path / filename
        if not source_file.exists():
            raise FileNotFoundError(f"Missing required source file: {source_file}")

        df = pd.read_csv(source_file)
        summary = CleaningSummary(
            dataset_name=filename,
            input_rows=len(df),
            output_rows=0,
            anomalies=[],
        )

        # Parse date-like columns where applicable.
        for col in df.columns:
            col_lower = col.lower()
            if col_lower == "month":
                parsed = pd.to_datetime(df[col].astype(str) + "-01", errors="coerce")
                parse_failures = int(parsed.isna().sum())
                if parse_failures:
                    summary.anomalies.append(
                        f"Unparseable month values in {col}: {parse_failures}"
                    )
                df[col] = parsed.dt.strftime("%Y-%m")
            elif "date" in col_lower:
                parsed = pd.to_datetime(df[col], errors="coerce")
                parse_failures = int(parsed.isna().sum())
                if parse_failures:
                    summary.anomalies.append(
                        f"Unparseable date values in {col}: {parse_failures}"
                    )
                # Persist in ISO date string format for consistent downstream loading.
                df[col] = parsed.dt.strftime("%Y-%m-%d")

        target_name = f"{source_file.stem}_cleaned.csv"
        target_file = processed_path / target_name
        df.to_csv(target_file, index=False)

        summary.output_rows = len(df)
        summaries.append(summary)
        print(f"Saved passthrough cleaned dataset: {target_name} ({len(df)} rows)")

    return summaries


def main() -> None:
    """Execute Day 2 cleaning pipeline and persist cleaned artifacts."""
    project_root = Path(__file__).resolve().parent.parent
    raw_path = project_root / "data" / "raw"
    processed_path = project_root / "data" / "processed"
    reports_path = project_root / "reports"

    processed_path.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)

    _print_section("DAY 2: DATA CLEANING STARTED")

    cleaned_nav, nav_summary = clean_nav_history(raw_path, processed_path)
    print(f"Saved cleaned NAV: {len(cleaned_nav)} rows")

    cleaned_txn, txn_summary = clean_investor_transactions(raw_path, processed_path)
    print(f"Saved cleaned investor transactions: {len(cleaned_txn)} rows")

    cleaned_perf, perf_summary = clean_scheme_performance(raw_path, processed_path)
    print(f"Saved cleaned scheme performance: {len(cleaned_perf)} rows")

    passthrough_summaries = passthrough_remaining_datasets(raw_path, processed_path)

    report_file = reports_path / "day2_cleaning_report.txt"
    all_summaries = [nav_summary, txn_summary, perf_summary, *passthrough_summaries]
    _write_cleaning_report(report_file, all_summaries)
    print(f"Cleaning report generated: {report_file}")

    _print_section("DAY 2: DATA CLEANING COMPLETED")


if __name__ == "__main__":
    main()
