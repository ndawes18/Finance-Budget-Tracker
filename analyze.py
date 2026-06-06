"""
analyze.py — Runs all budget analyses and prints formatted reports to terminal.
Usage: python analyze.py
"""

from queries import (
    get_conn, account_balances, net_worth, monthly_summary,
    income_vs_expense_by_category, budget_vs_actual, over_budget_alerts,
    top_merchants, weekend_vs_weekday, recurring_vs_discretionary,
    savings_goals_progress, monthly_savings_rate,
    upcoming_bills, annual_recurring_cost, recent_transactions,
    daily_spending_trend,
)
from datetime import datetime

# ── Formatting helpers ────────────────────────────────────────────────────────

def hr(char="─", width=74):
    print(char * width)

def section(title):
    print()
    hr("═")
    print(f"  {title}")
    hr("═")

def table(rows, headers, fmts=None):
    if not rows:
        print("  (no data)")
        return
    cols = len(headers)
    fmts = fmts or ["{}"] * cols
    str_rows = []
    for r in rows:
        vals = list(r)
        cells = []
        for i in range(cols):
            v = vals[i] if vals[i] is not None else 0
            try:
                cells.append(fmts[i].format(v))
            except (ValueError, TypeError):
                cells.append(str(v) if v is not None else "—")
        str_rows.append(cells)
    widths = [max(len(h), max(len(sr[i]) for sr in str_rows)) for i, h in enumerate(headers)]
    fmt_str = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt_str.format(*headers))
    hr()
    for sr in str_rows:
        print(fmt_str.format(*sr))


# ── Individual report sections ────────────────────────────────────────────────

def report_net_worth(conn):
    section("💼  NET WORTH OVERVIEW")
    r = net_worth(conn)
    print(f"  {'Total Assets':<28}  ${r['total_assets']:>12,.2f}")
    print(f"  {'Total Liabilities':<28}  ${r['total_liabilities']:>12,.2f}")
    hr()
    print(f"  {'NET WORTH':<28}  ${r['net_worth']:>12,.2f}")

    print()
    print("  Account Balances:")
    print(f"  {'Account':<26} {'Type':<12} {'Balance':>12}")
    hr()
    for a in account_balances(conn):
        sign = "-" if a["balance"] < 0 else " "
        print(f"  {a['name']:<26} {a['type']:<12} {sign}${abs(a['balance']):>11,.2f}")


def report_monthly_summary(conn):
    section("📅  MONTHLY CASHFLOW SUMMARY")
    rows = monthly_summary(conn)
    print(f"  {'Month':<10}  {'Income':>12}  {'Expenses':>12}  {'Net Cashflow':>13}  {'Txns':>5}")
    hr()
    for r in rows:
        net = r["net_cashflow"]
        indicator = "▲" if net >= 0 else "▼"
        print(f"  {r['month']:<10}  ${r['total_income']:>11,.2f}  "
              f"${r['total_expenses']:>11,.2f}  "
              f"{indicator} ${abs(net):>11,.2f}  {r['num_transactions']:>5}")


def report_budget_vs_actual(conn):
    section("🎯  BUDGET vs ACTUAL  (most recent month)")
    rows, ym = budget_vs_actual(conn)
    print(f"  Month: {ym}\n")
    print(f"  {'Category':<22}  {'Budgeted':>10}  {'Actual':>10}  {'Remaining':>10}  {'Used%':>7}  Status")
    hr()
    for r in rows:
        pct   = r["pct_used"] or 0
        bar   = "🔴" if pct > 100 else ("🟡" if pct > 80 else "🟢")
        rem   = r["remaining"]
        r_str = f"-${abs(rem):,.2f}" if rem < 0 else f" ${rem:,.2f}"
        print(f"  {r['category']:<22}  ${r['budgeted']:>9,.2f}  "
              f"${r['actual']:>9,.2f}  {r_str:>10}  {pct:>6.1f}%  {bar}")

    over, _ = over_budget_alerts(conn)
    if over:
        print(f"\n  ⚠️   {len(over)} categor{'y' if len(over)==1 else 'ies'} over budget!")
        for r in over:
            print(f"     • {r['category']}: spent ${r['actual']:,.2f} of ${r['budgeted']:,.2f} budget "
                  f"({r['pct_used']:.0f}%)")


def report_spending_by_category(conn):
    section("📊  SPENDING BY CATEGORY  (all time)")
    rows = income_vs_expense_by_category(conn)
    income_rows  = [r for r in rows if r["cat_type"] == "income"]
    expense_rows = [r for r in rows if r["cat_type"] == "expense"]

    print("  INCOME SOURCES:")
    print(f"  {'Category':<22}  {'Total':>12}  {'# Txns':>7}  {'Avg Txn':>10}")
    hr()
    for r in income_rows:
        print(f"  {r['category']:<22}  ${r['total_spent']:>11,.2f}  {r['num_txns']:>7}  ${r['avg_txn']:>9,.2f}")

    print("\n  EXPENSE CATEGORIES:")
    print(f"  {'Category':<22}  {'Total':>12}  {'# Txns':>7}  {'Avg Txn':>10}  {'Largest':>10}")
    hr()
    for r in expense_rows:
        print(f"  {r['category']:<22}  ${r['total_spent']:>11,.2f}  {r['num_txns']:>7}  "
              f"${r['avg_txn']:>9,.2f}  ${r['max_txn']:>9,.2f}")


def report_savings_rate(conn):
    section("💰  MONTHLY SAVINGS RATE")
    rows = monthly_savings_rate(conn)
    max_rate = max((r["savings_rate_pct"] or 0) for r in rows) or 1
    bar_w = 30
    print(f"  {'Month':<10}  {'Income':>10}  {'Expenses':>10}  {'Rate':>6}  Chart")
    hr()
    for r in rows:
        rate = r["savings_rate_pct"] or 0
        bar  = "█" * max(0, int(rate / max_rate * bar_w))
        flag = "🔴" if rate < 10 else ("🟡" if rate < 20 else "🟢")
        print(f"  {r['month']:<10}  ${r['income']:>9,.2f}  ${r['expenses']:>9,.2f}  "
              f"{rate:>5.1f}%  {flag} {bar}")


def report_savings_goals(conn):
    section("🏆  SAVINGS GOALS PROGRESS")
    rows = savings_goals_progress(conn)
    for r in rows:
        pct   = r["pct_complete"]
        filled = int(pct / 5)
        bar   = "█" * filled + "░" * (20 - filled)
        days  = f"{r['days_left']}d left" if r["days_left"] is not None else "no deadline"
        print(f"\n  {r['name']}  ({r['status']})")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Saved: ${r['saved_amount']:,.2f} / ${r['target_amount']:,.2f}   "
              f"Remaining: ${r['remaining']:,.2f}   {days}")


def report_top_merchants(conn):
    section("🏪  TOP MERCHANTS BY SPENDING")
    rows = top_merchants(conn, 12)
    table(
        rows,
        ["Merchant", "# Txns", "Total Spent", "Avg Txn", "First Seen", "Last Seen"],
        ["{}", "{}", "${:,.2f}", "${:,.2f}", "{}", "{}"],
    )


def report_recurring(conn):
    section("🔁  RECURRING vs DISCRETIONARY SPENDING")
    rows = recurring_vs_discretionary(conn)
    table(rows, ["Type", "# Txns", "Total Spent", "Avg Txn"],
          ["{}", "{}", "${:,.2f}", "${:,.2f}"])

    print()
    section("📋  ANNUAL RECURRING BILL COSTS")
    bills = annual_recurring_cost(conn)
    table(bills, ["Bill", "Amount", "Frequency", "Annual Cost", "Category"],
          ["{}", "${:,.2f}", "{}", "${:,.2f}", "{}"])
    total = sum(r["annual_cost"] for r in bills)
    print(f"\n  Total annual recurring cost: ${total:,.2f}  (${total/12:,.2f}/month)")


def report_upcoming_bills(conn):
    section("📆  UPCOMING BILLS  (next 30 days)")
    rows = upcoming_bills(conn, 30)
    if not rows:
        print("  No bills due in the next 30 days.")
        return
    table(rows, ["Bill", "Amount", "Frequency", "Due Date", "Category", "Account", "Days Away"],
          ["{}", "${:,.2f}", "{}", "{}", "{}", "{}", "{}"])


def report_weekend_vs_weekday(conn):
    section("📅  WEEKDAY vs WEEKEND SPENDING")
    rows = weekend_vs_weekday(conn)
    table(rows, ["Day Type", "# Txns", "Total Spent", "Avg/Txn", "Avg/Day"],
          ["{}", "{}", "${:,.2f}", "${:,.2f}", "${:,.2f}"])


def report_recent_transactions(conn):
    section("🧾  RECENT TRANSACTIONS  (last 20)")
    rows = recent_transactions(conn, 20)
    print(f"  {'Date':<12}  {'Description':<24}  {'Merchant':<18}  {'Category':<16}  {'Amount':>10}")
    hr()
    for r in rows:
        sign  = "+" if r["txn_type"] == "income" else "-"
        desc  = (r["description"] or "")[:23]
        merch = (r["merchant"]    or "")[:17]
        cat   = (r["category"]    or "")[:15]
        print(f"  {r['txn_date']:<12}  {desc:<24}  {merch:<18}  {cat:<16}  "
              f"{sign}${r['amount']:>9,.2f}")


# ── Entry point ───────────────────────────────────────────────────────────────

def run_all():
    print("\n" + "═"*74)
    print("   PERSONAL FINANCE & BUDGET TRACKER — FULL ANALYSIS REPORT")
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═"*74)

    with get_conn() as conn:
        report_net_worth(conn)
        report_monthly_summary(conn)
        report_budget_vs_actual(conn)
        report_spending_by_category(conn)
        report_savings_rate(conn)
        report_savings_goals(conn)
        report_top_merchants(conn)
        report_recurring(conn)
        report_upcoming_bills(conn)
        report_weekend_vs_weekday(conn)
        report_recent_transactions(conn)

    print("\n" + "═"*74)
    print("   END OF REPORT")
    print("═"*74 + "\n")


if __name__ == "__main__":
    run_all()
