"""
export_reports.py — Exports all analyses to CSV files in /reports.
Usage: python export_reports.py
"""

import csv
from pathlib import Path
from queries import (
    get_conn, account_balances, net_worth, monthly_summary,
    income_vs_expense_by_category, budget_vs_actual,
    top_merchants, monthly_savings_rate, savings_goals_progress,
    annual_recurring_cost, upcoming_bills, weekend_vs_weekday,
    recurring_vs_discretionary, recent_transactions,
)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


def write_csv(filename, rows):
    path = REPORTS_DIR / filename
    if not rows:
        print(f"  ⚠️  {filename} — no data"); return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow(list(r))
    print(f"  ✅  {filename}  ({len(rows)} rows)")


def write_kv_csv(filename, mapping):
    path = REPORTS_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value"])
        for k, v in mapping.items():
            w.writerow([k, v])
    print(f"  ✅  {filename}")


def run():
    print("\n📊  Exporting budget reports to /reports …\n")
    with get_conn() as conn:
        # Net worth
        nw = net_worth(conn)
        write_kv_csv("00_net_worth.csv", dict(nw))

        # Account balances
        write_csv("01_account_balances.csv",        account_balances(conn))
        write_csv("02_monthly_summary.csv",          monthly_summary(conn))

        bva, ym = budget_vs_actual(conn)
        write_csv(f"03_budget_vs_actual_{ym}.csv",  bva)

        write_csv("04_spending_by_category.csv",     income_vs_expense_by_category(conn))
        write_csv("05_monthly_savings_rate.csv",     monthly_savings_rate(conn))
        write_csv("06_savings_goals.csv",            savings_goals_progress(conn))
        write_csv("07_top_merchants.csv",            top_merchants(conn, 20))
        write_csv("08_annual_recurring_bills.csv",   annual_recurring_cost(conn))
        write_csv("09_upcoming_bills_30d.csv",       upcoming_bills(conn, 30))
        write_csv("10_weekend_vs_weekday.csv",       weekend_vs_weekday(conn))
        write_csv("11_recurring_vs_discretionary.csv", recurring_vs_discretionary(conn))
        write_csv("12_recent_transactions.csv",      recent_transactions(conn, 100))

    print(f"\n  Reports saved to: {REPORTS_DIR.resolve()}")


if __name__ == "__main__":
    run()
