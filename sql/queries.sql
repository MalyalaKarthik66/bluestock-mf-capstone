-- Day 2 Analytical SQL Queries for Bluestock Mutual Fund Analytics

-- Q1. Top 5 funds by AUM (latest performance snapshot)
SELECT
    d.amfi_code,
    d.scheme_name,
    d.fund_house,
    fp.aum_crore
FROM fact_performance fp
JOIN dim_fund d ON d.amfi_code = fp.amfi_code
ORDER BY fp.aum_crore DESC
LIMIT 5;

-- Q2. Average NAV per month across all funds
SELECT
    dd.year,
    dd.month,
    dd.month_name,
    ROUND(AVG(fn.nav), 4) AS avg_nav
FROM fact_nav fn
JOIN dim_date dd ON dd.date_key = fn.date_key
GROUP BY dd.year, dd.month, dd.month_name
ORDER BY dd.year, dd.month;

-- Q3. SIP YoY growth from monthly SIP inflow source table
WITH sip AS (
    SELECT
        CAST(SUBSTR(month, 1, 4) AS INTEGER) AS year,
        SUM(sip_inflow_crore) AS annual_sip_inflow_crore
    FROM "04_monthly_sip_inflows"
    GROUP BY CAST(SUBSTR(month, 1, 4) AS INTEGER)
)
SELECT
    year,
    annual_sip_inflow_crore,
    ROUND(
        100.0 * (annual_sip_inflow_crore - LAG(annual_sip_inflow_crore) OVER (ORDER BY year))
        / NULLIF(LAG(annual_sip_inflow_crore) OVER (ORDER BY year), 0),
        2
    ) AS yoy_growth_pct
FROM sip
ORDER BY year;

-- Q4. Transactions by state (count + amount)
SELECT
    state,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount_inr), 2) AS total_transaction_amount_inr
FROM fact_transactions
GROUP BY state
ORDER BY total_transaction_amount_inr DESC;

-- Q5. Funds with expense ratio below 1%
SELECT
    d.amfi_code,
    d.scheme_name,
    d.fund_house,
    fp.expense_ratio_pct,
    fp.return_3yr_pct,
    fp.sharpe_ratio
FROM fact_performance fp
JOIN dim_fund d ON d.amfi_code = fp.amfi_code
WHERE fp.expense_ratio_pct < 1.0
ORDER BY fp.expense_ratio_pct ASC, fp.return_3yr_pct DESC;

-- Q6. Top 10 funds by 3-year return
SELECT
    d.amfi_code,
    d.scheme_name,
    d.category,
    fp.return_3yr_pct,
    fp.alpha,
    fp.sharpe_ratio
FROM fact_performance fp
JOIN dim_fund d ON d.amfi_code = fp.amfi_code
ORDER BY fp.return_3yr_pct DESC
LIMIT 10;

-- Q7. Best risk-adjusted funds (Sharpe ratio ranking)
SELECT
    d.amfi_code,
    d.scheme_name,
    d.category,
    fp.sharpe_ratio,
    fp.sortino_ratio,
    fp.std_dev_ann_pct
FROM fact_performance fp
JOIN dim_fund d ON d.amfi_code = fp.amfi_code
ORDER BY fp.sharpe_ratio DESC
LIMIT 10;

-- Q8. Monthly transaction trend (volume + value)
SELECT
    dd.year,
    dd.month,
    dd.month_name,
    COUNT(*) AS transactions,
    ROUND(SUM(ft.amount_inr), 2) AS total_amount_inr
FROM fact_transactions ft
JOIN dim_date dd ON dd.date_key = ft.date_key
GROUP BY dd.year, dd.month, dd.month_name
ORDER BY dd.year, dd.month;

-- Q9. Category-level performance summary
SELECT
    d.category,
    COUNT(*) AS fund_count,
    ROUND(AVG(fp.return_1yr_pct), 2) AS avg_return_1yr_pct,
    ROUND(AVG(fp.return_3yr_pct), 2) AS avg_return_3yr_pct,
    ROUND(AVG(fp.sharpe_ratio), 2) AS avg_sharpe_ratio
FROM fact_performance fp
JOIN dim_fund d ON d.amfi_code = fp.amfi_code
GROUP BY d.category
ORDER BY avg_return_3yr_pct DESC;

-- Q10. Quarterly AUM trend by fund house
SELECT
    fa.fund_house,
    dd.year,
    dd.quarter,
    ROUND(SUM(fa.aum_crore), 2) AS total_aum_crore
FROM fact_aum fa
JOIN dim_date dd ON dd.date_key = fa.date_key
GROUP BY fa.fund_house, dd.year, dd.quarter
ORDER BY fa.fund_house, dd.year, dd.quarter;
