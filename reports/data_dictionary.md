# Bluestock Mutual Fund Analytics - Day 2 Data Dictionary

## Overview
This data dictionary documents the Day 2 star schema and supporting analytical table loaded into:

- SQLite DB: `data/db/bluestock_mf.db`

Source files used:
- Raw: `data/raw/01_fund_master.csv`, `data/raw/03_aum_by_fund_house.csv`, `data/raw/04_monthly_sip_inflows.csv`
- Cleaned: `data/processed/02_nav_history_cleaned.csv`, `data/processed/08_investor_transactions_cleaned.csv`, `data/processed/07_scheme_performance_cleaned.csv`

---

## Table: dim_fund
**Grain:** One row per mutual fund scheme (AMFI code)

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| amfi_code | INTEGER | Unique AMFI scheme code (primary identifier) | 01_fund_master.csv |
| scheme_name | TEXT | Full scheme name | 01_fund_master.csv |
| fund_house | TEXT | AMC / fund house name | 01_fund_master.csv |
| category | TEXT | Broad asset class (e.g., Equity, Debt, Hybrid) | 01_fund_master.csv |
| sub_category | TEXT | Sub-classification (e.g., Large Cap) | 01_fund_master.csv |
| plan | TEXT | Plan type (Regular/Direct) | 01_fund_master.csv |
| launch_date | DATE | Fund launch date | 01_fund_master.csv |
| benchmark | TEXT | Benchmark index for comparison | 01_fund_master.csv |
| expense_ratio_pct | REAL | Expense ratio percentage | 01_fund_master.csv |
| exit_load_pct | REAL | Exit load percentage | 01_fund_master.csv |
| min_sip_amount | REAL | Minimum SIP amount in INR | 01_fund_master.csv |
| min_lumpsum_amount | REAL | Minimum lumpsum amount in INR | 01_fund_master.csv |
| fund_manager | TEXT | Scheme fund manager | 01_fund_master.csv |
| risk_category | TEXT | Risk label (e.g., Moderate, High) | 01_fund_master.csv |
| sebi_category_code | TEXT | SEBI category code | 01_fund_master.csv |

---

## Table: dim_date
**Grain:** One row per calendar date referenced by facts

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| date_key | INTEGER | Surrogate date key in YYYYMMDD format | Derived from fact date columns |
| full_date | DATE | Actual calendar date | Derived from fact date columns |
| year | INTEGER | Calendar year | Derived |
| quarter | INTEGER | Calendar quarter (1-4) | Derived |
| month | INTEGER | Calendar month (1-12) | Derived |
| month_name | TEXT | Month name | Derived |
| week_of_year | INTEGER | ISO week number | Derived |
| day_of_month | INTEGER | Day number in month | Derived |
| day_name | TEXT | Weekday name | Derived |
| is_weekend | INTEGER | Weekend flag (1 weekend, 0 weekday) | Derived |

---

## Table: fact_nav
**Grain:** One row per scheme per date

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| nav_id | INTEGER | Surrogate row id | Generated in DB |
| amfi_code | INTEGER | Scheme code (FK to dim_fund) | 02_nav_history_cleaned.csv |
| date_key | INTEGER | Date key (FK to dim_date) | 02_nav_history_cleaned.csv + dim_date |
| nav | REAL | Net Asset Value for the scheme on date | 02_nav_history_cleaned.csv |

---

## Table: fact_transactions
**Grain:** One row per investor transaction

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| transaction_id | INTEGER | Surrogate row id | Generated in DB |
| investor_id | TEXT | Investor identifier | 08_investor_transactions_cleaned.csv |
| amfi_code | INTEGER | Scheme code (FK to dim_fund) | 08_investor_transactions_cleaned.csv |
| date_key | INTEGER | Transaction date key (FK to dim_date) | 08_investor_transactions_cleaned.csv + dim_date |
| transaction_type | TEXT | Transaction type (SIP/Lumpsum/Redemption) | 08_investor_transactions_cleaned.csv |
| amount_inr | REAL | Transaction amount in INR | 08_investor_transactions_cleaned.csv |
| state | TEXT | Investor state | 08_investor_transactions_cleaned.csv |
| city | TEXT | Investor city | 08_investor_transactions_cleaned.csv |
| city_tier | TEXT | City tier segment | 08_investor_transactions_cleaned.csv |
| age_group | TEXT | Investor age bucket | 08_investor_transactions_cleaned.csv |
| gender | TEXT | Investor gender | 08_investor_transactions_cleaned.csv |
| annual_income_lakh | REAL | Annual income in lakh INR | 08_investor_transactions_cleaned.csv |
| payment_mode | TEXT | Payment channel/mode | 08_investor_transactions_cleaned.csv |
| kyc_status | TEXT | KYC verification status | 08_investor_transactions_cleaned.csv |

---

## Table: fact_performance
**Grain:** One row per scheme at performance snapshot date

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| performance_id | INTEGER | Surrogate row id | Generated in DB |
| amfi_code | INTEGER | Scheme code (FK to dim_fund) | 07_scheme_performance_cleaned.csv |
| as_of_date_key | INTEGER | Snapshot date key (FK to dim_date) | Derived in loader |
| return_1yr_pct | REAL | 1-year return percentage | 07_scheme_performance_cleaned.csv |
| return_3yr_pct | REAL | 3-year return percentage | 07_scheme_performance_cleaned.csv |
| return_5yr_pct | REAL | 5-year return percentage | 07_scheme_performance_cleaned.csv |
| benchmark_3yr_pct | REAL | Benchmark 3-year return | 07_scheme_performance_cleaned.csv |
| alpha | REAL | Risk-adjusted excess return metric | 07_scheme_performance_cleaned.csv |
| beta | REAL | Market sensitivity metric | 07_scheme_performance_cleaned.csv |
| sharpe_ratio | REAL | Risk-adjusted return metric | 07_scheme_performance_cleaned.csv |
| sortino_ratio | REAL | Downside-risk-adjusted return metric | 07_scheme_performance_cleaned.csv |
| std_dev_ann_pct | REAL | Annualized volatility | 07_scheme_performance_cleaned.csv |
| max_drawdown_pct | REAL | Max drawdown percentage | 07_scheme_performance_cleaned.csv |
| aum_crore | REAL | Scheme AUM in crore INR | 07_scheme_performance_cleaned.csv |
| expense_ratio_pct | REAL | Expense ratio percentage | 07_scheme_performance_cleaned.csv |
| morningstar_rating | REAL | Morningstar rating | 07_scheme_performance_cleaned.csv |
| risk_grade | TEXT | Risk grade label | 07_scheme_performance_cleaned.csv |

---

## Table: fact_aum
**Grain:** One row per fund house per reporting date

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| aum_id | INTEGER | Surrogate row id | Generated in DB |
| fund_house | TEXT | Fund house/AMC name | 03_aum_by_fund_house.csv |
| date_key | INTEGER | Reporting date key (FK to dim_date) | 03_aum_by_fund_house.csv + dim_date |
| aum_lakh_crore | REAL | AUM in lakh crore INR | 03_aum_by_fund_house.csv |
| aum_crore | REAL | AUM in crore INR | 03_aum_by_fund_house.csv |
| num_schemes | INTEGER | Number of schemes for fund house at date | 03_aum_by_fund_house.csv |

---

## Supporting Table: 04_monthly_sip_inflows
**Purpose:** Supports SIP YoY analytical query

| Column | Data Type | Business Meaning | Source Dataset |
|---|---|---|---|
| month | TEXT | Year-month period | 04_monthly_sip_inflows.csv |
| sip_inflow_crore | REAL | Monthly SIP inflow in crore INR | 04_monthly_sip_inflows.csv |
| active_sip_accounts_crore | REAL | Active SIP accounts in crore | 04_monthly_sip_inflows.csv |
| new_sip_accounts_lakh | REAL | New SIP accounts in lakh | 04_monthly_sip_inflows.csv |
| sip_aum_lakh_crore | REAL | SIP AUM in lakh crore INR | 04_monthly_sip_inflows.csv |
| yoy_growth_pct | REAL | YoY growth percentage (source-provided) | 04_monthly_sip_inflows.csv |
