"""
Day 2 SQLite Loader for Bluestock Mutual Fund Analytics Project.

This script:
1. Builds a star schema in SQLite using sql/schema.sql.
2. Loads cleaned Day 2 datasets plus required dimensions/facts.
3. Verifies database row counts against source cleaned CSV/dataframes.
4. Writes verification report to reports/day2_db_load_report.txt.

Uses SQLAlchemy create_engine() and pandas to_sql() per project requirements.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
from sqlalchemy import create_engine, text


def _print_section(title: str) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)


def _build_dim_date(date_series: Iterable[pd.Timestamp]) -> pd.DataFrame:
    """Create dim_date dataframe from a collection of dates."""
    dates = pd.to_datetime(pd.Series(date_series).dropna().unique())
    if len(dates) == 0:
        raise ValueError("No dates available to build dim_date.")

    dim = pd.DataFrame({"full_date": pd.to_datetime(dates)})
    dim = dim.drop_duplicates().sort_values("full_date").reset_index(drop=True)

    dim["date_key"] = dim["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"] = dim["full_date"].dt.year
    dim["quarter"] = dim["full_date"].dt.quarter
    dim["month"] = dim["full_date"].dt.month
    dim["month_name"] = dim["full_date"].dt.strftime("%B")
    dim["week_of_year"] = dim["full_date"].dt.isocalendar().week.astype(int)
    dim["day_of_month"] = dim["full_date"].dt.day
    dim["day_name"] = dim["full_date"].dt.strftime("%A")
    dim["is_weekend"] = (dim["full_date"].dt.dayofweek >= 5).astype(int)

    return dim[
        [
            "date_key",
            "full_date",
            "year",
            "quarter",
            "month",
            "month_name",
            "week_of_year",
            "day_of_month",
            "day_name",
            "is_weekend",
        ]
    ]


def _execute_schema(engine, schema_path: Path) -> None:
    """Execute SQL schema script against SQLite database."""
    sql_text = schema_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in [s.strip() for s in sql_text.split(";") if s.strip()]:
            conn.execute(text(statement))


def _to_sql(df: pd.DataFrame, table_name: str, engine, if_exists: str = "append") -> None:
    """Helper wrapper to write DataFrame to SQLite table."""
    df.to_sql(table_name, con=engine, if_exists=if_exists, index=False)


def main() -> None:
    """Build star schema, load data, and verify row counts."""
    project_root = Path(__file__).resolve().parent.parent
    raw_path = project_root / "data" / "raw"
    processed_path = project_root / "data" / "processed"
    db_path = project_root / "data" / "db" / "bluestock_mf.db"
    sql_path = project_root / "sql"
    reports_path = project_root / "reports"

    db_path.parent.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)

    # Source files
    fund_master_file = raw_path / "01_fund_master.csv"
    aum_file = raw_path / "03_aum_by_fund_house.csv"
    sip_monthly_file = raw_path / "04_monthly_sip_inflows.csv"

    nav_clean_file = processed_path / "02_nav_history_cleaned.csv"
    txn_clean_file = processed_path / "08_investor_transactions_cleaned.csv"
    perf_clean_file = processed_path / "07_scheme_performance_cleaned.csv"

    for req in [
        fund_master_file,
        aum_file,
        sip_monthly_file,
        nav_clean_file,
        txn_clean_file,
        perf_clean_file,
        sql_path / "schema.sql",
    ]:
        if not req.exists():
            raise FileNotFoundError(f"Required file missing: {req}")

    _print_section("DAY 2: SQLITE LOAD STARTED")

    # Read source data
    dim_fund = pd.read_csv(fund_master_file)
    fact_nav_src = pd.read_csv(nav_clean_file)
    fact_txn_src = pd.read_csv(txn_clean_file)
    fact_perf_src = pd.read_csv(perf_clean_file)
    fact_aum_src = pd.read_csv(aum_file)
    sip_monthly_src = pd.read_csv(sip_monthly_file)

    # Parse date fields
    dim_fund["launch_date"] = pd.to_datetime(dim_fund["launch_date"], errors="coerce")
    fact_nav_src["date"] = pd.to_datetime(fact_nav_src["date"], errors="coerce")
    fact_txn_src["transaction_date"] = pd.to_datetime(
        fact_txn_src["transaction_date"], errors="coerce"
    )
    fact_aum_src["date"] = pd.to_datetime(fact_aum_src["date"], errors="coerce")

    # Performance as-of date: use max available NAV date for consistent snapshot key.
    perf_as_of_date = fact_nav_src["date"].max()
    if pd.isna(perf_as_of_date):
        raise ValueError("Could not derive performance as_of_date from cleaned NAV data.")

    # Build date dimension from all relevant date columns
    dim_date = _build_dim_date(
        pd.concat(
            [
                fact_nav_src["date"],
                fact_txn_src["transaction_date"],
                fact_aum_src["date"],
                pd.Series([perf_as_of_date]),
            ],
            ignore_index=True,
        )
    )

    # Prepare fact tables with keys
    date_key_map = dict(zip(dim_date["full_date"].dt.date, dim_date["date_key"]))

    fact_nav = fact_nav_src.copy()
    fact_nav["date_key"] = fact_nav["date"].dt.date.map(date_key_map)
    fact_nav = fact_nav[["amfi_code", "date_key", "nav"]].dropna().copy()
    fact_nav["date_key"] = fact_nav["date_key"].astype(int)

    fact_txn = fact_txn_src.copy()
    fact_txn["date_key"] = fact_txn["transaction_date"].dt.date.map(date_key_map)
    fact_txn = fact_txn[
        [
            "investor_id",
            "amfi_code",
            "date_key",
            "transaction_type",
            "amount_inr",
            "state",
            "city",
            "city_tier",
            "age_group",
            "gender",
            "annual_income_lakh",
            "payment_mode",
            "kyc_status",
        ]
    ].dropna(subset=["amfi_code", "date_key", "amount_inr"])
    fact_txn["date_key"] = fact_txn["date_key"].astype(int)

    fact_perf = fact_perf_src.copy()
    fact_perf["as_of_date_key"] = int(pd.Timestamp(perf_as_of_date).strftime("%Y%m%d"))
    fact_perf = fact_perf[
        [
            "amfi_code",
            "as_of_date_key",
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
            "risk_grade",
        ]
    ].dropna(subset=["amfi_code", "as_of_date_key"])

    fact_aum = fact_aum_src.copy()
    fact_aum["date_key"] = fact_aum["date"].dt.date.map(date_key_map)
    fact_aum = fact_aum[
        ["fund_house", "date_key", "aum_lakh_crore", "aum_crore", "num_schemes"]
    ].dropna(subset=["fund_house", "date_key"])
    fact_aum["date_key"] = fact_aum["date_key"].astype(int)

    # SQLAlchemy engine
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    # Build schema
    _execute_schema(engine, sql_path / "schema.sql")

    # Load tables
    _to_sql(dim_fund, "dim_fund", engine)
    _to_sql(dim_date, "dim_date", engine)
    _to_sql(fact_nav, "fact_nav", engine)
    _to_sql(fact_txn, "fact_transactions", engine)
    _to_sql(fact_perf, "fact_performance", engine)
    _to_sql(fact_aum, "fact_aum", engine)
    _to_sql(sip_monthly_src, "04_monthly_sip_inflows", engine, if_exists="replace")

    # Verify row counts
    expected_counts: Dict[str, int] = {
        "dim_fund": len(dim_fund),
        "dim_date": len(dim_date),
        "fact_nav": len(fact_nav),
        "fact_transactions": len(fact_txn),
        "fact_performance": len(fact_perf),
        "fact_aum": len(fact_aum),
    }

    actual_counts: Dict[str, int] = {}
    with engine.connect() as conn:
        for table in expected_counts:
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            actual_counts[table] = int(row_count.scalar_one())

    report_file = reports_path / "day2_db_load_report.txt"
    with report_file.open("w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DAY 2 SQLITE LOAD REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Database: {db_path}\n\n")

        all_match = True
        for table in expected_counts:
            exp = expected_counts[table]
            act = actual_counts[table]
            status = "PASS" if exp == act else "FAIL"
            if status == "FAIL":
                all_match = False
            f.write(f"{table:<20} expected={exp:<8} actual={act:<8} status={status}\n")

        f.write("\nOverall row-count verification: ")
        f.write("PASS\n" if all_match else "FAIL\n")

    # Console summary
    _print_section("DAY 2: SQLITE LOAD COMPLETED")
    for table in expected_counts:
        print(
            f"{table:<20} expected={expected_counts[table]:<8} actual={actual_counts[table]:<8}"
        )
    print(f"Row-count verification report: {report_file}")


if __name__ == "__main__":
    main()
