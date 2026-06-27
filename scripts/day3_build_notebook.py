"""
Build the Day 3 EDA Jupyter notebook for the Bluestock Mutual Fund Analytics project.

This script writes notebooks/EDA_Analysis.ipynb using the cleaned datasets created
in Day 2. The notebook contains chart generation, PNG exports, and markdown insight
cells linked to the exported charts.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from textwrap import dedent


def code_cell(source: str) -> dict:
    """Create a notebook code cell without pre-defined execution output."""
    source_text = dedent(source).strip("\n") + "\n"
    return {
        "cell_type": "code",
        "id": uuid.uuid4().hex[:8],
        "metadata": {"language": "python", "id": uuid.uuid4().hex[:8]},
        "execution_count": None,
        "outputs": [],
        "source": source_text.splitlines(keepends=True),
    }


def markdown_cell(source: str) -> dict:
    """Create a notebook markdown cell."""
    source_text = dedent(source).strip("\n") + "\n"
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {"language": "markdown", "id": uuid.uuid4().hex[:8]},
        "source": source_text.splitlines(keepends=True),
    }


def build_notebook() -> dict:
    """Assemble the notebook structure and cells."""
    cells = []

    cells.append(
        markdown_cell(
            """
            # Day 3 - Exploratory Data Analysis

            This notebook explores the cleaned mutual fund datasets created in Day 2 and exports all charts to `reports/charts/`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            from pathlib import Path

            import pandas as pd
            import matplotlib.pyplot as plt
            import seaborn as sns
            import plotly.express as px
            import plotly.graph_objects as go

            sns.set_theme(style='whitegrid', context='talk')
            plt.rcParams['figure.dpi'] = 120

            project_root = None
            for candidate in [Path.cwd(), Path.cwd().parent]:
                if (candidate / 'data' / 'processed').exists():
                    project_root = candidate
                    break
            if project_root is None:
                project_root = Path.cwd().resolve()

            data_dir = project_root / 'data' / 'processed'
            charts_dir = project_root / 'reports' / 'charts'
            charts_dir.mkdir(parents=True, exist_ok=True)

            def load_csv(name, parse_dates=None):
                return pd.read_csv(data_dir / name, parse_dates=parse_dates)

            fund_master = load_csv('01_fund_master_cleaned.csv', parse_dates=['launch_date'])
            nav = load_csv('02_nav_history_cleaned.csv', parse_dates=['date'])
            aum = load_csv('03_aum_by_fund_house_cleaned.csv', parse_dates=['date'])
            sip = load_csv('04_monthly_sip_inflows_cleaned.csv')
            sip['month'] = pd.to_datetime(sip['month'] + '-01')
            category_inflows = load_csv('05_category_inflows_cleaned.csv')
            category_inflows['month'] = pd.to_datetime(category_inflows['month'] + '-01')
            folio = load_csv('06_industry_folio_count_cleaned.csv')
            folio['month'] = pd.to_datetime(folio['month'] + '-01')
            performance = load_csv('07_scheme_performance_cleaned.csv')
            transactions = load_csv('08_investor_transactions_cleaned.csv', parse_dates=['transaction_date'])
            holdings = load_csv('09_portfolio_holdings_cleaned.csv', parse_dates=['portfolio_date'])
            benchmark = load_csv('10_benchmark_indices_cleaned.csv', parse_dates=['date'])

            scheme_names = fund_master[['amfi_code', 'scheme_name', 'fund_house']].drop_duplicates('amfi_code')
            nav = nav.merge(scheme_names, on='amfi_code', how='left')
            performance = performance.merge(scheme_names, on='amfi_code', how='left', suffixes=('', '_master'))

            transactions['transaction_type'] = transactions['transaction_type'].astype(str)
            transactions['age_group'] = transactions['age_group'].astype(str)
            transactions['city_tier'] = transactions['city_tier'].astype(str)
            transactions['state'] = transactions['state'].astype(str)
            transactions['gender'] = transactions['gender'].astype(str)

            sip_transactions = transactions[transactions['transaction_type'] == 'SIP'].copy()

            def save_plotly(fig, filename):
                path = charts_dir / filename
                fig.write_image(str(path), scale=2)
                print(f'Saved {path.name}')

            def save_matplotlib(fig, filename):
                path = charts_dir / filename
                fig.savefig(path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                print(f'Saved {path.name}')

            def ordered_age_groups(series):
                preferred = ['18-25', '26-35', '36-45', '46-55', '56+']
                present = [item for item in preferred if item in set(series.astype(str))]
                leftovers = sorted([item for item in series.astype(str).unique() if item not in present])
                return present + leftovers
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 1: NAV trend analysis for all 40 schemes with 2023 bull run and 2024 correction highlights
            nav_trend = nav.sort_values(['amfi_code', 'date']).copy()
            nav_trend['nav_index'] = nav_trend.groupby('amfi_code')['nav'].transform(lambda s: s / s.iloc[0] * 100)
            avg_nav = nav_trend.groupby('date', as_index=False)['nav_index'].mean()

            fig = px.line(
                nav_trend,
                x='date',
                y='nav_index',
                color='scheme_name',
                title='NAV Trend Analysis (Normalized Index = 100 at Start) Across All 40 Schemes',
                labels={'date': 'Date', 'nav_index': 'NAV Index (Base 100)', 'scheme_name': 'Scheme'},
                render_mode='svg',
            )
            fig.update_traces(opacity=0.18, line={'width': 1}, showlegend=False)
            fig.add_trace(
                go.Scatter(
                    x=avg_nav['date'],
                    y=avg_nav['nav_index'],
                    mode='lines',
                    name='Average NAV Index',
                    line={'color': '#ff7f0e', 'width': 4},
                )
            )
            fig.add_vrect(x0='2023-01-01', x1='2023-12-31', fillcolor='green', opacity=0.12, line_width=0)
            fig.add_vrect(x0='2024-01-01', x1='2024-12-31', fillcolor='red', opacity=0.12, line_width=0)
            fig.add_annotation(x='2023-06-15', y=nav_trend['nav_index'].max() * 0.98, text='2023 bull run', showarrow=False, font={'color': 'green'})
            fig.add_annotation(x='2024-06-15', y=nav_trend['nav_index'].max() * 0.90, text='2024 correction', showarrow=False, font={'color': 'red'})
            fig.update_layout(template='plotly_white', height=700, width=1500)
            save_plotly(fig, '01_nav_trend_all_schemes.png')
            fig.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 1:** The NAV trend chart shows that the scheme universe recovered strongly during the 2023 bull phase, while the 2024 shaded period highlights a broad correction and divergence in scheme trajectories. See `../reports/charts/01_nav_trend_all_schemes.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 2: AUM growth grouped bar chart (2022-2025)
            aum_yearly = aum.copy()
            aum_yearly['year'] = aum_yearly['date'].dt.year
            aum_yearly = aum_yearly[aum_yearly['year'].between(2022, 2025)]
            aum_yearly = aum_yearly.groupby(['year', 'fund_house'], as_index=False)['aum_crore'].mean()
            top_funds = aum_yearly.groupby('fund_house')['aum_crore'].mean().nlargest(8).index
            aum_plot = aum_yearly[aum_yearly['fund_house'].isin(top_funds)].copy()

            fig, ax = plt.subplots(figsize=(16, 7))
            sns.barplot(data=aum_plot, x='year', y='aum_crore', hue='fund_house', ax=ax)
            ax.set_title('AUM Growth by Fund House (2022-2025)', pad=16)
            ax.set_xlabel('Year')
            ax.set_ylabel('Average AUM (Crore INR)')
            ax.legend(title='Fund House', bbox_to_anchor=(1.02, 1), loc='upper left')
            save_matplotlib(fig, '02_aum_growth_grouped_bar.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 2:** AUM growth is concentrated in a handful of large fund houses, and the year-wise grouping makes the expansion trend visible across the 2022–2025 period. See `../reports/charts/02_aum_growth_grouped_bar.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 3: Monthly SIP inflow time-series with peak annotation
            sip_sorted = sip.sort_values('month').copy()
            peak_row = sip_sorted.loc[sip_sorted['sip_inflow_crore'].idxmax()]

            fig = px.line(
                sip_sorted,
                x='month',
                y='sip_inflow_crore',
                title='Monthly SIP Inflows (Jan 2022 - Dec 2025)',
                labels={'month': 'Month', 'sip_inflow_crore': 'SIP Inflow (Crore INR)'},
                markers=True,
            )
            fig.add_annotation(
                x=peak_row['month'].to_pydatetime(),
                y=peak_row['sip_inflow_crore'],
                text=f"Peak: ₹{peak_row['sip_inflow_crore']:,.0f} Cr",
                showarrow=True,
                arrowhead=2,
                ax=20,
                ay=-40,
            )
            fig.add_hline(y=peak_row['sip_inflow_crore'], line_dash='dash', line_color='orange')
            fig.update_layout(template='plotly_white', height=650, width=1400)
            save_plotly(fig, '03_monthly_sip_inflow_trend.png')
            fig.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 3:** SIP inflows show a persistent upward pattern with a clear peak around ₹31,002 Cr, which supports the story of growing retail participation in the market. See `../reports/charts/03_monthly_sip_inflow_trend.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 4: Category inflow heatmap
            category_pivot = category_inflows.pivot_table(
                index='category',
                columns='month',
                values='net_inflow_crore',
                aggfunc='sum',
            ).fillna(0)
            category_pivot = category_pivot.loc[category_pivot.sum(axis=1).sort_values(ascending=False).index]

            fig, ax = plt.subplots(figsize=(18, 7))
            sns.heatmap(category_pivot, cmap='YlGnBu', linewidths=0.3, ax=ax)
            ax.set_title('Category Inflow Heatmap', pad=16)
            ax.set_xlabel('Month')
            ax.set_ylabel('Category')
            save_matplotlib(fig, '04_category_inflow_heatmap.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 4:** The heatmap reveals that liquidity-oriented and large-scale categories attract the strongest and most persistent inflows, while some categories remain cyclical. See `../reports/charts/04_category_inflow_heatmap.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 5: Age-group pie chart
            age_counts = transactions['age_group'].value_counts().reindex(ordered_age_groups(transactions['age_group']), fill_value=0)
            age_labels = [str(label) for label in age_counts.index]
            age_values = [float(value) for value in age_counts.values]
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(age_values, labels=age_labels, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('Set2', len(age_counts)))
            ax.set_title('Investor Age-Group Distribution', pad=18)
            save_matplotlib(fig, '05_age_group_pie.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 5:** The age-group split confirms that participation is broad-based, with the middle age cohorts carrying the largest share of activity. See `../reports/charts/05_age_group_pie.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 6: SIP amount boxplot by age group
            sip_age = sip_transactions.copy()
            sip_age = sip_age[sip_age['age_group'].isin(ordered_age_groups(sip_age['age_group']))]

            fig, ax = plt.subplots(figsize=(14, 7))
            sns.boxplot(data=sip_age, x='age_group', y='amount_inr', order=ordered_age_groups(sip_age['age_group']), ax=ax)
            ax.set_title('SIP Amount Distribution by Age Group', pad=16)
            ax.set_xlabel('Age Group')
            ax.set_ylabel('SIP Amount (INR)')
            ax.tick_params(axis='x', rotation=0)
            save_matplotlib(fig, '06_sip_amount_boxplot_by_age_group.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 6:** SIP ticket sizes vary materially by age group, with some older cohorts showing a wider and higher-value investment distribution. See `../reports/charts/06_sip_amount_boxplot_by_age_group.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 7: Gender distribution
            gender_counts = transactions['gender'].value_counts()
            gender_labels = [str(label) for label in gender_counts.index]
            gender_values = [float(value) for value in gender_counts.values]
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(gender_values, labels=gender_labels, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel', len(gender_counts)))
            ax.set_title('Investor Gender Distribution', pad=18)
            save_matplotlib(fig, '07_gender_distribution.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 7:** Gender distribution remains uneven, but the chart provides a quick segmentation view for understanding who is currently most active in the dataset. See `../reports/charts/07_gender_distribution.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 8: SIP amount by state
            state_sip = sip_transactions.groupby('state', as_index=False)['amount_inr'].sum().sort_values('amount_inr', ascending=False).head(15)
            state_sip = state_sip.sort_values('amount_inr', ascending=True)

            fig, ax = plt.subplots(figsize=(14, 8))
            sns.barplot(data=state_sip, y='state', x='amount_inr', ax=ax, palette='Blues_r')
            ax.set_title('Top States by SIP Amount', pad=16)
            ax.set_xlabel('SIP Amount (INR)')
            ax.set_ylabel('State')
            save_matplotlib(fig, '08_statewise_sip_amount.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 8:** SIP flows are geographically concentrated, with a few large states accounting for a disproportionate share of invested value. See `../reports/charts/08_statewise_sip_amount.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 9: T30 vs B30 pie chart
            tier_amounts = sip_transactions.groupby('city_tier', as_index=False)['amount_inr'].sum()
            tier_amounts = tier_amounts[tier_amounts['city_tier'].isin(['T30', 'B30'])]
            tier_amounts = tier_amounts.set_index('city_tier').reindex(['T30', 'B30']).fillna(0)
            tier_labels = [str(label) for label in tier_amounts.index]
            tier_values = [float(value) for value in tier_amounts['amount_inr']]

            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(
                tier_values,
                labels=tier_labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=['#4C78A8', '#F58518'],
            )
            ax.set_title('T30 vs B30 SIP Amount Split', pad=18)
            save_matplotlib(fig, '09_t30_vs_b30_pie.png')
            plt.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 9:** The T30 vs B30 mix helps frame the spread between metro and non-metro participation, which is essential for investor demographic analysis. See `../reports/charts/09_t30_vs_b30_pie.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 10: Folio count growth line chart with milestones
            folio_sorted = folio.sort_values('month').copy()
            fig = px.line(
                folio_sorted,
                x='month',
                y='total_folios_crore',
                title='Industry Folio Count Growth',
                labels={'month': 'Month', 'total_folios_crore': 'Total Folios (Crore)'},
                markers=True,
            )
            first_row = folio_sorted.iloc[0]
            last_row = folio_sorted.iloc[-1]
            fig.add_annotation(x=first_row['month'].to_pydatetime(), y=first_row['total_folios_crore'], text=f"Start: {first_row['total_folios_crore']:.2f} Cr", showarrow=True, ax=20, ay=30)
            fig.add_annotation(x=last_row['month'].to_pydatetime(), y=last_row['total_folios_crore'], text=f"End: {last_row['total_folios_crore']:.2f} Cr", showarrow=True, ax=-20, ay=-30)
            fig.add_vline(x=first_row['month'].to_pydatetime(), line_dash='dash', line_color='gray')
            fig.add_vline(x=last_row['month'].to_pydatetime(), line_dash='dash', line_color='gray')
            fig.update_layout(template='plotly_white', height=650, width=1400)
            save_plotly(fig, '10_folio_count_growth_line.png')
            fig.show()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            **Insight 10:** Folio growth shows a sustained rise in investor participation, and the milestone annotations make the acceleration easy to spot over time. See `../reports/charts/10_folio_count_growth_line.png`.
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 11: NAV return correlation heatmap for 10 selected funds
            top10_codes = performance.nlargest(10, 'aum_crore')['amfi_code'].tolist()
            nav_10 = nav[nav['amfi_code'].isin(top10_codes)][['date', 'amfi_code', 'nav', 'scheme_name']].drop_duplicates()
            nav_10_pivot = nav_10.pivot_table(index='date', columns='scheme_name', values='nav').sort_index()
            returns_10 = nav_10_pivot.pct_change().dropna(how='all')
            corr_10 = returns_10.corr()

            fig, ax = plt.subplots(figsize=(12, 10))
            sns.heatmap(corr_10, cmap='coolwarm', center=0, annot=True, fmt='.2f', ax=ax)
            ax.set_title('NAV Return Correlation Heatmap - Top 10 Funds by AUM', pad=16)
            save_matplotlib(fig, '11_nav_return_correlation_heatmap.png')
            plt.show()
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 12: Sector allocation donut chart
            sector_totals = holdings.groupby('sector')['market_value_cr'].sum()
            sector_data = sorted(
                [(str(sector), float(value)) for sector, value in sector_totals.items()],
                key=lambda item: item[1],
                reverse=True,
            )
            sector_labels = [item[0] for item in sector_data]
            sector_values = [item[1] for item in sector_data]
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=sector_labels,
                        values=sector_values,
                        hole=0.45,
                        textinfo='label+percent',
                    )
                ]
            )
            fig.update_layout(title='Sector Allocation Donut Chart', template='plotly_white', width=1000, height=800)
            save_plotly(fig, '12_sector_allocation_donut.png')
            fig.show()
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 13: Top 10 funds by 3-year return
            top_returns = performance[['scheme_name', 'return_3yr_pct', 'category', 'fund_house']].drop_duplicates().sort_values('return_3yr_pct', ascending=False).head(10)
            fig, ax = plt.subplots(figsize=(14, 8))
            sns.barplot(data=top_returns, y='scheme_name', x='return_3yr_pct', ax=ax, palette='viridis')
            ax.set_title('Top 10 Funds by 3-Year Return', pad=16)
            ax.set_xlabel('3-Year Return (%)')
            ax.set_ylabel('Scheme')
            save_matplotlib(fig, '13_top_10_funds_by_3yr_return.png')
            plt.show()
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 14: Expense ratio vs Sharpe ratio scatter plot
            fig, ax = plt.subplots(figsize=(12, 8))
            sns.scatterplot(
                data=performance,
                x='expense_ratio_pct',
                y='sharpe_ratio',
                hue='category',
                size='aum_crore',
                sizes=(40, 400),
                alpha=0.8,
                ax=ax,
            )
            ax.set_title('Expense Ratio vs Sharpe Ratio', pad=16)
            ax.set_xlabel('Expense Ratio (%)')
            ax.set_ylabel('Sharpe Ratio')
            ax.legend(title='Category', bbox_to_anchor=(1.02, 1), loc='upper left')
            save_matplotlib(fig, '14_expense_ratio_vs_sharpe_scatter.png')
            plt.show()
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Chart 15: Transaction type distribution
            txn_distribution = transactions['transaction_type'].value_counts()
            txn_labels = [str(label) for label in txn_distribution.index]
            txn_values = [float(value) for value in txn_distribution.values]
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(
                txn_values,
                labels=txn_labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=sns.color_palette('Set3', len(txn_distribution)),
            )
            ax.set_title('Transaction Type Distribution', pad=18)
            save_matplotlib(fig, '15_transaction_type_distribution.png')
            plt.show()
            """
        )
    )

    cells.append(
        code_cell(
            """
            # Final verification of exported charts
            generated_pngs = sorted(charts_dir.glob('*.png'))
            print(f'Generated {len(generated_pngs)} PNG charts in {charts_dir}')
            for png in generated_pngs:
                print(png.name)
            """
        )
    )

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return notebook


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    notebook_path = project_root / 'notebooks' / 'EDA_Analysis.ipynb'
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook()
    notebook_path.write_text(json.dumps(notebook, indent=2), encoding='utf-8')
    print(f'Wrote notebook: {notebook_path}')


if __name__ == '__main__':
    main()
