"""
Data Ingestion Script for Bluestock Mutual Fund Analytics Project

This script performs the initial data loading and quality assessment for the 10
provided CSV datasets. It is the first step in the ETL pipeline.

Key Functions:
1.  Loads all 10 raw CSV files from the 'data/raw' directory into pandas DataFrames.
2.  For each dataset, it performs and prints a basic exploratory analysis, including:
    -   Dataset shape (rows, columns)
    -   Column data types (dtypes)
    -   The first 3 rows of the data (head)
    -   A summary of anomalies:
        -   Count of missing values per column.
        -   Total count of duplicate rows.
        -   Checks for negative values in numeric columns where they are not expected.
3.  Conducts a specific exploration of the '01_fund_master.csv' dataset to understand
    the variety of funds, categories, and plans.
4.  Performs a critical validation of AMFI codes by cross-referencing
    '01_fund_master.csv' and '02_nav_history.csv' to ensure data integrity.
5.  Generates a comprehensive Data Quality Summary report in 'reports/data_quality_summary.txt',
    documenting the findings from the analysis for audit and review.

This script is designed to be run as the first step of the data processing workflow.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

def analyze_dataset(df, name, file_path):
    """Analyzes a single DataFrame and prints its characteristics and anomalies."""
    print("-" * 50)
    print(f"Analyzing: {name} ({file_path.name})")
    print("-" * 50)

    # --- Basic Info ---
    print(f"Shape: {df.shape}")
    print("\nData Types:\n", df.dtypes)
    print("\nHead:\n", df.head(3))

    # --- Anomaly Detection ---
    print("\nAnomalies:")
    
    # 1. Missing Values
    missing_values = df.isnull().sum()
    print(f"  - Missing Values per column:\n{missing_values[missing_values > 0]}")
    
    # 2. Duplicate Rows
    duplicate_rows = df.duplicated().sum()
    print(f"  - Duplicate Rows: {duplicate_rows}")

    # 3. Negative Values in numeric columns (where not expected)
    numeric_cols = df.select_dtypes(include=['number']).columns
    negative_counts = {}
    for col in numeric_cols:
        # Exclude columns where negatives might be valid (like returns, alpha)
        if 'return' not in col and 'alpha' not in col and 'beta' not in col and 'drawdown' not in col:
            count = (df[col] < 0).sum()
            if count > 0:
                negative_counts[col] = count
    if negative_counts:
        print(f"  - Unexpected Negative Values: {negative_counts}")
    
    print("\n")
    return {
        "name": name,
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing_values": missing_values.sum(),
        "duplicate_rows": duplicate_rows,
    }

def main():
    """Main function to orchestrate the data ingestion and analysis process."""
    # --- Setup Paths ---
    # Use __file__ to get the path of the current script, then navigate to project root
    project_root = Path(__file__).resolve().parent.parent
    raw_data_path = project_root / "data" / "raw"
    reports_path = project_root / "reports"
    reports_path.mkdir(exist_ok=True) # Ensure reports directory exists

    # --- Define Datasets ---
    dataset_files = {
        "fund_master": "01_fund_master.csv",
        "nav_history": "02_nav_history.csv",
        "aum_by_fund_house": "03_aum_by_fund_house.csv",
        "monthly_sip_inflows": "04_monthly_sip_inflows.csv",
        "category_inflows": "05_category_inflows.csv",
        "industry_folio_count": "06_industry_folio_count.csv",
        "scheme_performance": "07_scheme_performance.csv",
        "investor_transactions": "08_investor_transactions.csv",
        "portfolio_holdings": "09_portfolio_holdings.csv",
        "benchmark_indices": "10_benchmark_indices.csv",
    }

    dataframes = {}
    quality_report_data = []

    # --- Load and Analyze Each Dataset ---
    print("=" * 80)
    print("STARTING DATA INGESTION AND QUALITY ANALYSIS")
    print("=" * 80)

    for name, filename in dataset_files.items():
        file_path = raw_data_path / filename
        if not file_path.exists():
            print(f"ERROR: File not found at {file_path}", file=sys.stderr)
            continue
        
        try:
            df = pd.read_csv(file_path)
            dataframes[name] = df
            report_item = analyze_dataset(df, name, file_path)
            quality_report_data.append(report_item)
        except Exception as e:
            print(f"ERROR: Could not load or analyze {filename}. Reason: {e}", file=sys.stderr)

    # --- Fund Master Exploration ---
    print("=" * 80)
    print("FUND MASTER EXPLORATION")
    print("=" * 80)
    if "fund_master" in dataframes:
        df_master = dataframes["fund_master"]
        print("Unique Fund Houses:\n", df_master["fund_house"].unique())
        print("\nUnique Categories:\n", df_master["category"].unique())
        print("\nUnique Sub-Categories:\n", df_master["sub_category"].unique())
        print("\nUnique Risk Categories:\n", df_master["risk_category"].unique())
        print("\nPlan Counts (Regular vs Direct):\n", df_master["plan"].value_counts())
    else:
        print("Fund Master data not available for exploration.")
    print("\n")

    # --- AMFI Code Validation ---
    print("=" * 80)
    print("AMFI CODE VALIDATION (fund_master vs nav_history)")
    print("=" * 80)
    amfi_validation_result = "SKIPPED: Required dataframes not loaded."
    if "fund_master" in dataframes and "nav_history" in dataframes:
        master_codes = set(dataframes["fund_master"]["amfi_code"])
        nav_codes = set(dataframes["nav_history"]["amfi_code"])

        master_not_in_nav = master_codes - nav_codes
        nav_not_in_master = nav_codes - master_codes

        if not master_not_in_nav and not nav_not_in_master:
            amfi_validation_result = "PASS: All AMFI codes in fund_master and nav_history match perfectly."
            print(amfi_validation_result)
        else:
            amfi_validation_result = "FAIL: Mismatch found in AMFI codes."
            print(amfi_validation_result)
            if master_not_in_nav:
                print(f"  - Codes in fund_master but NOT in nav_history: {master_not_in_nav}")
                amfi_validation_result += f"\n  - Master but not in NAV: {master_not_in_nav}"
            if nav_not_in_master:
                print(f"  - Codes in nav_history but NOT in fund_master: {nav_not_in_master}")
                amfi_validation_result += f"\n  - NAV but not in Master: {nav_not_in_master}"
    print("\n")

    # --- Generate Data Quality Summary Report ---
    summary_path = reports_path / "data_quality_summary.txt"
    print(f"Generating data quality summary at: {summary_path}")
    with open(summary_path, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("      DATA QUALITY SUMMARY REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("-" * 30 + "\n")
        f.write("1. File Row & Column Counts\n")
        f.write("-" * 30 + "\n")
        for item in quality_report_data:
            f.write(f"- {item['name']:<25}: {item['rows']} rows, {item['columns']} columns\n")
        f.write("\n")

        f.write("-" * 30 + "\n")
        f.write("2. Missing Value Counts\n")
        f.write("-" * 30 + "\n")
        for item in quality_report_data:
            f.write(f"- {item['name']:<25}: {item['missing_values']} total missing values\n")
        f.write("\n")

        f.write("-" * 30 + "\n")
        f.write("3. Duplicate Row Counts\n")
        f.write("-" * 30 + "\n")
        for item in quality_report_data:
            f.write(f"- {item['name']:<25}: {item['duplicate_rows']} duplicate rows\n")
        f.write("\n")

        f.write("-" * 30 + "\n")
        f.write("4. AMFI Code Validation\n")
        f.write("-" * 30 + "\n")
        f.write(f"{amfi_validation_result}\n\n")

        f.write("-" * 30 + "\n")
        f.write("5. General Anomalies\n")
        f.write("-" * 30 + "\n")
        f.write("Check console output for details on unexpected negative values per dataset.\n")

    print("=" * 80)
    print("DATA INGESTION AND ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
