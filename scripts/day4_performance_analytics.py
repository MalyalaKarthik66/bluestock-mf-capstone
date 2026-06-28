"""
Day 4: Fund Performance Analytics
Standalone execution script for all performance calculations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.stats import linregress
from datetime import datetime, timedelta
from typing import Any
import warnings
import os

warnings.filterwarnings('ignore')

# Configure matplotlib for headless execution
plt.switch_backend('Agg')

# Configure plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Define file paths
project_root = Path(__file__).parent.parent
data_processed_dir = project_root / 'data' / 'processed'
data_raw_dir = project_root / 'data' / 'raw'
reports_dir = project_root / 'reports'
charts_dir = reports_dir / 'charts'

# Create charts directory if it doesn't exist
charts_dir.mkdir(parents=True, exist_ok=True)

print("="*80)
print("DAY 4: FUND PERFORMANCE ANALYTICS - EXECUTION START")
print("="*80)
print(f"Project root: {project_root}")
print(f"Data processed: {data_processed_dir}")
print(f"Charts: {charts_dir}")

# Load data
print("\n[1/11] Loading data...")
nav_history = pd.read_csv(data_processed_dir / '02_nav_history_cleaned.csv')
fund_master = pd.read_csv(data_processed_dir / '01_fund_master_cleaned.csv')
benchmark_indices = pd.read_csv(data_processed_dir / '10_benchmark_indices_cleaned.csv')

# Convert date columns
nav_history['date'] = pd.to_datetime(nav_history['date'])
benchmark_indices['date'] = pd.to_datetime(benchmark_indices['date'])
fund_master['launch_date'] = pd.to_datetime(fund_master['launch_date'], errors='coerce')

# Sort data
nav_history = nav_history.sort_values('date').reset_index(drop=True)
benchmark_indices = benchmark_indices.sort_values('date').reset_index(drop=True)

print(f"✓ Data loaded: {nav_history.shape[0]} NAV records, {fund_master.shape[0]} funds")

# Task 1: Compute daily returns
print("\n[2/11] Computing daily returns...")
nav_pivot = nav_history.pivot_table(index='date', columns='amfi_code', values='nav')
daily_returns = nav_pivot.pct_change()

returns_export = daily_returns.reset_index()
returns_export.to_csv(data_processed_dir / 'returns_computed.csv', index=False)
print(f"✓ Daily returns saved: {returns_export.shape}")

# Task 2: Compute CAGR
print("\n[3/11] Computing CAGR (1yr, 3yr, 5yr)...")

def compute_cagr(nav_series, periods_years):
    cagr_dict = {}
    end_nav = nav_series.iloc[-1]
    
    for period in periods_years:
        lookback_days = int(period * 252)
        
        if len(nav_series) > lookback_days:
            start_nav = nav_series.iloc[-lookback_days]
            cagr = (end_nav / start_nav) ** (1 / period) - 1
        else:
            cagr = np.nan
        
        cagr_dict[f'{period}yr_cagr'] = cagr
    
    return cagr_dict

cagr_results = []
periods = [1, 3, 5]

for amfi_code in nav_pivot.columns:
    fund_nav = nav_pivot[amfi_code].dropna()
    
    if len(fund_nav) > 0:
        fund_info = fund_master[fund_master['amfi_code'] == amfi_code].iloc[0]
        cagr_vals = compute_cagr(fund_nav, periods)
        
        row = {
            'amfi_code': amfi_code,
            'scheme_name': fund_info['scheme_name'],
            'fund_house': fund_info['fund_house'],
            'category': fund_info['category'],
        }
        row.update(cagr_vals)
        cagr_results.append(row)

cagr_report = pd.DataFrame(cagr_results)
cagr_report.to_csv(data_processed_dir / 'cagr_report.csv', index=False)
print(f"✓ CAGR report saved: {len(cagr_report)} funds")

# Task 3: Compute Sharpe Ratio
print("\n[4/11] Computing Sharpe Ratios...")

rf_annual = 0.065
rf_daily = rf_annual / 252

sharpe_results = []

for amfi_code in daily_returns.columns:
    fund_returns = daily_returns[amfi_code].dropna()
    
    if len(fund_returns) > 1:
        avg_return = fund_returns.mean()
        std_return = fund_returns.std()
        
        if std_return > 0:
            sharpe = ((avg_return - rf_daily) / std_return) * np.sqrt(252)
        else:
            sharpe = np.nan
        
        fund_info = fund_master[fund_master['amfi_code'] == amfi_code].iloc[0]
        
        row = {
            'amfi_code': amfi_code,
            'scheme_name': fund_info['scheme_name'],
            'fund_house': fund_info['fund_house'],
            'category': fund_info['category'],
            'sharpe_ratio': sharpe,
            'avg_daily_return_pct': avg_return * 100,
            'annual_return_pct': avg_return * 252 * 100,
            'daily_std_pct': std_return * 100,
            'annual_std_pct': std_return * np.sqrt(252) * 100,
        }
        sharpe_results.append(row)

sharpe_df = pd.DataFrame(sharpe_results)
sharpe_df.to_csv(data_processed_dir / 'sharpe_values.csv', index=False)
print(f"✓ Sharpe ratios saved: {len(sharpe_df)} funds")

# Task 4: Compute Sortino Ratio
print("\n[5/11] Computing Sortino Ratios...")

sortino_results = []

for amfi_code in daily_returns.columns:
    fund_returns = daily_returns[amfi_code].dropna()
    
    if len(fund_returns) > 1:
        avg_return = fund_returns.mean()
        
        downside_returns = fund_returns[fund_returns < 0]
        
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
        else:
            downside_std = 0
        
        if downside_std > 0:
            sortino = ((avg_return - rf_daily) / downside_std) * np.sqrt(252)
        else:
            sortino = np.nan
        
        fund_info = fund_master[fund_master['amfi_code'] == amfi_code].iloc[0]
        
        row = {
            'amfi_code': amfi_code,
            'scheme_name': fund_info['scheme_name'],
            'fund_house': fund_info['fund_house'],
            'category': fund_info['category'],
            'sortino_ratio': sortino,
            'avg_daily_return_pct': avg_return * 100,
            'downside_std_daily_pct': downside_std * 100,
            'downside_std_annual_pct': downside_std * np.sqrt(252) * 100,
            'num_negative_days': len(downside_returns),
            'pct_negative_days': len(downside_returns) / len(fund_returns) * 100,
        }
        sortino_results.append(row)

sortino_df = pd.DataFrame(sortino_results)
sortino_df.to_csv(data_processed_dir / 'sortino_values.csv', index=False)
print(f"✓ Sortino ratios saved: {len(sortino_df)} funds")

# Task 5: Compute Alpha and Beta
print("\n[6/11] Computing Alpha and Beta vs NIFTY100...")

nifty100 = benchmark_indices[benchmark_indices['index_name'] == 'NIFTY100'].copy()
nifty100 = nifty100.sort_values('date').reset_index(drop=True)

nifty100_pivot = nifty100.set_index('date')['close_value'].sort_index()
nifty100_returns = nifty100_pivot.pct_change().dropna()

alpha_beta_results = []

for amfi_code in daily_returns.columns:
    fund_returns = daily_returns[amfi_code].dropna()
    
    common_dates = fund_returns.index.intersection(nifty100_returns.index)
    
    if len(common_dates) > 10:
        fund_ret_aligned = fund_returns.loc[common_dates].values
        nifty_ret_aligned = nifty100_returns.loc[common_dates].values
        
        linreg_result: Any = linregress(nifty_ret_aligned, fund_ret_aligned)
        slope = float(linreg_result.slope)
        intercept = float(linreg_result.intercept)
        r_value = float(linreg_result.rvalue)
        
        alpha_annualized = intercept * 252
        
        fund_info = fund_master[fund_master['amfi_code'] == amfi_code].iloc[0]
        
        row = {
            'amfi_code': amfi_code,
            'scheme_name': fund_info['scheme_name'],
            'fund_house': fund_info['fund_house'],
            'category': fund_info['category'],
            'beta': slope,
            'alpha_annualized_pct': alpha_annualized * 100,
            'intercept_daily': intercept,
            'r_squared': r_value ** 2,
            'correlation': r_value,
            'num_observations': len(common_dates),
        }
        alpha_beta_results.append(row)

alpha_beta_df = pd.DataFrame(alpha_beta_results)
alpha_beta_df.to_csv(data_processed_dir / 'alpha_beta.csv', index=False)
print(f"✓ Alpha and Beta saved: {len(alpha_beta_df)} funds")

# Task 6: Compute Maximum Drawdown
print("\n[7/11] Computing Maximum Drawdown...")

def compute_max_drawdown_with_dates(nav_series):
    running_max = nav_series.expanding().max()
    drawdown = (nav_series / running_max) - 1
    
    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()
    
    peak_idx = running_max[:trough_idx].idxmax()
    
    peak_nav = nav_series[peak_idx]
    trough_nav = nav_series[trough_idx]
    
    return max_dd, peak_idx, trough_idx, peak_nav, trough_nav

max_drawdown_results = []

for amfi_code in nav_pivot.columns:
    fund_nav = nav_pivot[amfi_code].dropna()
    
    if len(fund_nav) > 10:
        max_dd, peak_date, trough_date, peak_nav, trough_nav = compute_max_drawdown_with_dates(fund_nav)
        
        fund_info = fund_master[fund_master['amfi_code'] == amfi_code].iloc[0]
        
        row = {
            'amfi_code': amfi_code,
            'scheme_name': fund_info['scheme_name'],
            'fund_house': fund_info['fund_house'],
            'category': fund_info['category'],
            'max_drawdown_pct': max_dd * 100,
            'peak_date': peak_date.strftime('%Y-%m-%d'),
            'trough_date': trough_date.strftime('%Y-%m-%d'),
            'peak_nav': peak_nav,
            'trough_nav': trough_nav,
            'drawdown_duration_days': (trough_date - peak_date).days,
        }
        max_drawdown_results.append(row)

max_drawdown_df = pd.DataFrame(max_drawdown_results)
max_drawdown_df.to_csv(data_processed_dir / 'max_drawdown.csv', index=False)
print(f"✓ Maximum Drawdown saved: {len(max_drawdown_df)} funds")

# Task 7: Build Fund Scorecard
print("\n[8/11] Building Fund Scorecard...")

scorecard_data = fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category', 'expense_ratio_pct']].copy()

cagr_3yr = cagr_report[['amfi_code', '3yr_cagr']].copy()
cagr_3yr.columns = ['amfi_code', 'cagr_3yr']
scorecard_data = scorecard_data.merge(cagr_3yr, on='amfi_code', how='left')

sharpe_merge = sharpe_df[['amfi_code', 'sharpe_ratio']].copy()
scorecard_data = scorecard_data.merge(sharpe_merge, on='amfi_code', how='left')

alpha_merge = alpha_beta_df[['amfi_code', 'alpha_annualized_pct']].copy()
alpha_merge.columns = ['amfi_code', 'alpha_pct']
scorecard_data = scorecard_data.merge(alpha_merge, on='amfi_code', how='left')

dd_merge = max_drawdown_df[['amfi_code', 'max_drawdown_pct']].copy()
scorecard_data = scorecard_data.merge(dd_merge, on='amfi_code', how='left')

# Rank each metric
scorecard_data['cagr_rank'] = scorecard_data['cagr_3yr'].rank(method='min', na_option='bottom')
scorecard_data['sharpe_rank'] = scorecard_data['sharpe_ratio'].rank(method='min', na_option='bottom')
scorecard_data['alpha_rank'] = scorecard_data['alpha_pct'].rank(method='min', na_option='bottom')

scorecard_data['expense_rank_raw'] = scorecard_data['expense_ratio_pct'].rank(method='min', na_option='bottom')
scorecard_data['expense_rank'] = scorecard_data.shape[0] + 1 - scorecard_data['expense_rank_raw']

scorecard_data['dd_rank_raw'] = scorecard_data['max_drawdown_pct'].rank(method='min', na_option='bottom')
scorecard_data['dd_rank'] = scorecard_data.shape[0] + 1 - scorecard_data['dd_rank_raw']

# Normalize ranks to 0-100 scale
n_funds = scorecard_data.shape[0]

scorecard_data['cagr_score'] = (scorecard_data['cagr_rank'] / n_funds) * 100
scorecard_data['sharpe_score'] = (scorecard_data['sharpe_rank'] / n_funds) * 100
scorecard_data['alpha_score'] = (scorecard_data['alpha_rank'] / n_funds) * 100
scorecard_data['expense_score'] = (scorecard_data['expense_rank'] / n_funds) * 100
scorecard_data['dd_score'] = (scorecard_data['dd_rank'] / n_funds) * 100

# Calculate composite score
weights = {
    'cagr_score': 0.30,
    'sharpe_score': 0.25,
    'alpha_score': 0.20,
    'expense_score': 0.15,
    'dd_score': 0.10,
}

scorecard_data['composite_score'] = (
    scorecard_data['cagr_score'] * weights['cagr_score'] +
    scorecard_data['sharpe_score'] * weights['sharpe_score'] +
    scorecard_data['alpha_score'] * weights['alpha_score'] +
    scorecard_data['expense_score'] * weights['expense_score'] +
    scorecard_data['dd_score'] * weights['dd_score']
)

scorecard_data['overall_rank'] = scorecard_data['composite_score'].rank(method='min', ascending=False)

scorecard_export = scorecard_data[[
    'amfi_code', 'scheme_name', 'fund_house', 'category', 'expense_ratio_pct',
    'cagr_3yr', 'sharpe_ratio', 'alpha_pct', 'max_drawdown_pct',
    'cagr_score', 'sharpe_score', 'alpha_score', 'expense_score', 'dd_score',
    'composite_score', 'overall_rank'
]].copy()

scorecard_export.to_csv(data_processed_dir / 'fund_scorecard.csv', index=False)
print(f"✓ Fund Scorecard saved: {len(scorecard_export)} funds")

# Task 8: Benchmark comparison chart
print("\n[9/11] Creating benchmark comparison chart...")

top_5_funds = scorecard_export.head(5)['amfi_code'].tolist()

start_date = pd.Timestamp('2023-01-01')
end_date = nav_history['date'].max()

nav_filtered = nav_history[(nav_history['date'] >= start_date) & (nav_history['date'] <= end_date)].copy()
bench_filtered = benchmark_indices[(benchmark_indices['date'] >= start_date) & (benchmark_indices['date'] <= end_date)].copy()

nav_pivot_filtered = nav_filtered.pivot_table(index='date', columns='amfi_code', values='nav')

top_5_navs = nav_pivot_filtered[top_5_funds].copy()
top_5_indexed = (top_5_navs / top_5_navs.iloc[0]) * 100

nifty50 = bench_filtered[bench_filtered['index_name'] == 'NIFTY50'].copy()
nifty100_bench = bench_filtered[bench_filtered['index_name'] == 'NIFTY100'].copy()

nifty50_pivot = nifty50.set_index('date')['close_value'].sort_index()
nifty100_pivot = nifty100_bench.set_index('date')['close_value'].sort_index()

nifty50_indexed = (nifty50_pivot / nifty50_pivot.iloc[0]) * 100
nifty100_indexed = (nifty100_pivot / nifty100_pivot.iloc[0]) * 100

fig, ax = plt.subplots(figsize=(14, 8))

colors_funds = plt.get_cmap('Set1')(np.linspace(0, 1, 5))
for i, fund_code in enumerate(top_5_funds):
    fund_name = scorecard_export[scorecard_export['amfi_code'] == fund_code]['scheme_name'].values[0]
    ax.plot(top_5_indexed.index, top_5_indexed[fund_code], label=f'Top {i+1}: {fund_name[:40]}...', 
            linewidth=2.5, color=colors_funds[i])

ax.plot(nifty50_indexed.index, nifty50_indexed, label='NIFTY 50', 
        linewidth=2.5, color='red', linestyle='--', alpha=0.8)
ax.plot(nifty100_indexed.index, nifty100_indexed, label='NIFTY 100', 
        linewidth=2.5, color='orange', linestyle='--', alpha=0.8)

ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Indexed Value (100 at start)', fontsize=12, fontweight='bold')
ax.set_title('Top 5 Funds vs NIFTY Benchmarks (Indexed, 2023-2026)', fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_facecolor('#f8f9fa')

plt.tight_layout()
plt.savefig(charts_dir / 'benchmark_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Benchmark comparison chart saved")

# Task 9-10: Tracking error analysis
print("\n[10/11] Computing tracking error analysis...")

print(f"\nTracking Error Analysis:")
print("=" * 80)

for fund_code in top_5_funds:
    fund_name = scorecard_export[scorecard_export['amfi_code'] == fund_code]['scheme_name'].values[0]
    
    fund_nav = nav_pivot_filtered[fund_code].dropna()
    fund_returns_local = fund_nav.pct_change().dropna()
    
    common_dates = fund_returns_local.index.intersection(nifty50_indexed.index)
    
    if len(common_dates) > 10:
        fund_ret = fund_returns_local.loc[common_dates].values
        nifty50_ret = nifty50_indexed.loc[common_dates].pct_change().dropna().values
        nifty100_ret = nifty100_indexed.loc[common_dates].pct_change().dropna().values
        
        min_len = min(len(fund_ret), len(nifty50_ret), len(nifty100_ret))
        fund_ret = fund_ret[-min_len:]
        nifty50_ret = nifty50_ret[-min_len:]
        nifty100_ret = nifty100_ret[-min_len:]
        
        te_nifty50 = np.std(fund_ret - nifty50_ret) * np.sqrt(252)
        te_nifty100 = np.std(fund_ret - nifty100_ret) * np.sqrt(252)
        
        excess_nifty50 = (fund_ret.mean() - nifty50_ret.mean()) * 252 * 100
        excess_nifty100 = (fund_ret.mean() - nifty100_ret.mean()) * 252 * 100
        
        print(f"\n{fund_name[:50]}:")
        print(f"  Tracking Error vs NIFTY50: {te_nifty50*100:.2f}%")
        print(f"  Tracking Error vs NIFTY100: {te_nifty100*100:.2f}%")
        print(f"  Excess Return vs NIFTY50: {excess_nifty50:.2f}%")
        print(f"  Excess Return vs NIFTY100: {excess_nifty100:.2f}%")

# Final verification
print("\n[11/11] Final verification...")
print("\n" + "="*80)
print("DAY 4: FUND PERFORMANCE ANALYTICS - COMPLETION CHECKLIST")
print("="*80)

expected_files = {
    'returns_computed.csv': 'Daily returns for all 40 funds',
    'cagr_report.csv': 'CAGR for 1yr, 3yr, 5yr periods',
    'sharpe_values.csv': 'Sharpe ratios',
    'sortino_values.csv': 'Sortino ratios',
    'alpha_beta.csv': 'Alpha and Beta vs Nifty 100',
    'max_drawdown.csv': 'Maximum Drawdown analysis',
    'fund_scorecard.csv': 'Composite Fund Scorecard (0-100)',
}

print("\n[CSV Output Files]")
all_pass = True
for filename, description in expected_files.items():
    filepath = data_processed_dir / filename
    if filepath.exists():
        file_size = filepath.stat().st_size
        num_rows = len(pd.read_csv(filepath))
        print(f"✓ PASS: {filename}")
        print(f"         {description} | Rows: {num_rows}")
    else:
        print(f"✗ FAIL: {filename} - FILE NOT FOUND")
        all_pass = False

print("\n[Visualization Output]")
chart_file = charts_dir / 'benchmark_comparison.png'
if chart_file.exists():
    file_size = chart_file.stat().st_size
    print(f"✓ PASS: benchmark_comparison.png ({file_size:,} bytes)")
else:
    print(f"✗ FAIL: benchmark_comparison.png - FILE NOT FOUND")
    all_pass = False

print("\n" + "="*80)
print("REQUIREMENTS SUMMARY")
print("="*80)

requirements = [
    ("Task 1", "Compute daily returns", (data_processed_dir / 'returns_computed.csv').exists()),
    ("Task 2", "Compute CAGR (1yr, 3yr, 5yr)", (data_processed_dir / 'cagr_report.csv').exists()),
    ("Task 3", "Compute Sharpe Ratio", (data_processed_dir / 'sharpe_values.csv').exists()),
    ("Task 4", "Compute Sortino Ratio", (data_processed_dir / 'sortino_values.csv').exists()),
    ("Task 5", "Compute Alpha and Beta", (data_processed_dir / 'alpha_beta.csv').exists()),
    ("Task 6", "Compute Maximum Drawdown", (data_processed_dir / 'max_drawdown.csv').exists()),
    ("Task 7", "Build Fund Scorecard", (data_processed_dir / 'fund_scorecard.csv').exists()),
    ("Task 8", "Benchmark comparison chart", chart_file.exists()),
]

pass_count = 0
for task_id, task_name, status in requirements:
    status_str = "✓ PASS" if status else "✗ FAIL"
    print(f"{status_str}: {task_id} - {task_name}")
    if status:
        pass_count += 1

print("\n" + "="*80)
print(f"OVERALL RESULT: {pass_count}/{len(requirements)} TASKS PASSED")
print("="*80)

if pass_count == len(requirements):
    print("\n✓ ALL DAY 4 REQUIREMENTS COMPLETED SUCCESSFULLY!")
else:
    print(f"\n✗ {len(requirements) - pass_count} task(s) failed.")

print("\n" + "="*80)
print("EXECUTION COMPLETE")
print("="*80)
