"""
queries.py — All SQL analysis functions for the budget tracker.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/budget.db")


def get_conn():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run setup_db.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
#  ACCOUNT OVERVIEW
# ─────────────────────────────────────────────

def account_balances(conn):
    """Current balance of every active account."""
    return conn.execute("""
        SELECT name, type, balance, currency
        FROM accounts
        WHERE is_active = 1
        ORDER BY CASE type
            WHEN 'checking'    THEN 1
            WHEN 'savings'     THEN 2
            WHEN 'investment'  THEN 3
            WHEN 'credit'      THEN 4
            WHEN 'cash'        THEN 5
        END
    """).fetchall()


def net_worth(conn):
    """Assets minus liabilities."""
    return conn.execute("""
        SELECT
            ROUND(SUM(CASE WHEN type != 'credit' THEN balance ELSE 0 END), 2) AS total_assets,
            ROUND(ABS(SUM(CASE WHEN type = 'credit' AND balance < 0 THEN balance ELSE 0 END)), 2) AS total_liabilities,
            ROUND(SUM(balance), 2) AS net_worth
        FROM accounts
        WHERE is_active = 1
    """).fetchone()


# ─────────────────────────────────────────────
#  INCOME & EXPENSE SUMMARY
# ─────────────────────────────────────────────

def monthly_summary(conn):
    """Total income, expenses, and net per month."""
    return conn.execute("""
        SELECT
            strftime('%Y-%m', txn_date)                          AS month,
            ROUND(SUM(CASE WHEN txn_type='income'  THEN amount ELSE 0 END), 2) AS total_income,
            ROUND(SUM(CASE WHEN txn_type='expense' THEN amount ELSE 0 END), 2) AS total_expenses,
            ROUND(
                SUM(CASE WHEN txn_type='income'  THEN amount ELSE 0 END) -
                SUM(CASE WHEN txn_type='expense' THEN amount ELSE 0 END), 2
            )                                                    AS net_cashflow,
            COUNT(*)                                             AS num_transactions
        FROM transactions
        GROUP BY month
        ORDER BY month
    """).fetchall()


def income_vs_expense_by_category(conn, year_month=None):
    """Spending per category for a given month (or all time)."""
    cond = "AND strftime('%Y-%m', t.txn_date) = ?" if year_month else ""
    params = (year_month,) if year_month else ()
    return conn.execute(f"""
        SELECT
            c.name                          AS category,
            c.type                          AS cat_type,
            ROUND(SUM(t.amount), 2)         AS total_spent,
            COUNT(t.id)                     AS num_txns,
            ROUND(AVG(t.amount), 2)         AS avg_txn,
            ROUND(MAX(t.amount), 2)         AS max_txn
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE 1=1 {cond}
        GROUP BY c.id
        ORDER BY c.type, total_spent DESC
    """, params).fetchall()


# ─────────────────────────────────────────────
#  BUDGET vs ACTUAL
# ─────────────────────────────────────────────

def budget_vs_actual(conn, year_month=None):
    """
    Compare budgeted vs actual spending per expense category.
    Defaults to the most recent month with data.
    """
    if not year_month:
        row = conn.execute(
            "SELECT strftime('%Y-%m', MAX(txn_date)) FROM transactions"
        ).fetchone()
        year_month = row[0]

    return conn.execute("""
        SELECT
            c.name                                           AS category,
            COALESCE(mb.budget_amt, c.monthly_budget, 0)    AS budgeted,
            COALESCE(ROUND(SUM(t.amount), 2), 0)            AS actual,
            ROUND(COALESCE(mb.budget_amt, c.monthly_budget, 0)
                  - COALESCE(SUM(t.amount), 0), 2)          AS remaining,
            CASE
                WHEN COALESCE(mb.budget_amt, c.monthly_budget, 1) = 0 THEN NULL
                ELSE ROUND(COALESCE(SUM(t.amount),0)
                     / COALESCE(mb.budget_amt, c.monthly_budget, 1) * 100, 1)
            END                                              AS pct_used
        FROM categories c
        LEFT JOIN monthly_budgets mb
               ON mb.category_id = c.id AND mb.year_month = ?
        LEFT JOIN transactions t
               ON t.category_id = c.id
              AND t.txn_type = 'expense'
              AND strftime('%Y-%m', t.txn_date) = ?
        WHERE c.type = 'expense'
        GROUP BY c.id
        ORDER BY pct_used DESC NULLS LAST
    """, (year_month, year_month)).fetchall(), year_month


def over_budget_alerts(conn, year_month=None):
    """Categories where actual spending exceeded the budget."""
    rows, ym = budget_vs_actual(conn, year_month)
    return [r for r in rows if r["pct_used"] and r["pct_used"] > 100], ym


# ─────────────────────────────────────────────
#  SPENDING PATTERNS
# ─────────────────────────────────────────────

def top_merchants(conn, limit=15):
    """Where the most money is being spent."""
    return conn.execute("""
        SELECT
            merchant,
            COUNT(*)                    AS num_txns,
            ROUND(SUM(amount), 2)       AS total_spent,
            ROUND(AVG(amount), 2)       AS avg_txn,
            MIN(txn_date)               AS first_seen,
            MAX(txn_date)               AS last_seen
        FROM transactions
        WHERE txn_type = 'expense' AND merchant IS NOT NULL
        GROUP BY merchant
        ORDER BY total_spent DESC
        LIMIT ?
    """, (limit,)).fetchall()


def daily_spending_trend(conn):
    """Total expenses per day (last 90 days)."""
    return conn.execute("""
        SELECT
            txn_date                        AS day,
            ROUND(SUM(amount), 2)           AS total_spent,
            COUNT(*)                        AS num_txns
        FROM transactions
        WHERE txn_type = 'expense'
          AND txn_date >= date('now', '-90 days')
        GROUP BY txn_date
        ORDER BY txn_date
    """).fetchall()


def weekend_vs_weekday(conn):
    """Compare spending on weekdays vs weekends."""
    return conn.execute("""
        SELECT
            CASE CAST(strftime('%w', txn_date) AS INTEGER)
                WHEN 0 THEN 'Weekend'
                WHEN 6 THEN 'Weekend'
                ELSE 'Weekday'
            END                                     AS day_type,
            COUNT(*)                                AS num_txns,
            ROUND(SUM(amount), 2)                   AS total_spent,
            ROUND(AVG(amount), 2)                   AS avg_per_txn,
            ROUND(SUM(amount) / COUNT(DISTINCT txn_date), 2) AS avg_per_day
        FROM transactions
        WHERE txn_type = 'expense'
        GROUP BY day_type
    """).fetchall()


def recurring_vs_discretionary(conn):
    """Split spending into recurring (bills) vs one-off purchases."""
    return conn.execute("""
        SELECT
            CASE is_recurring WHEN 1 THEN 'Recurring' ELSE 'Discretionary' END AS spend_type,
            COUNT(*)                        AS num_txns,
            ROUND(SUM(amount), 2)           AS total_spent,
            ROUND(AVG(amount), 2)           AS avg_txn
        FROM transactions
        WHERE txn_type = 'expense'
        GROUP BY is_recurring
        ORDER BY is_recurring DESC
    """).fetchall()


# ─────────────────────────────────────────────
#  SAVINGS & GOALS
# ─────────────────────────────────────────────

def savings_goals_progress(conn):
    """Progress toward each savings goal."""
    return conn.execute("""
        SELECT
            g.name,
            g.target_amount,
            g.saved_amount,
            ROUND(g.saved_amount / g.target_amount * 100, 1)   AS pct_complete,
            ROUND(g.target_amount - g.saved_amount, 2)          AS remaining,
            g.deadline,
            a.name                                               AS account,
            CASE g.is_complete WHEN 1 THEN 'Complete' ELSE 'In Progress' END AS status,
            CASE
                WHEN g.deadline IS NULL THEN NULL
                ELSE CAST(julianday(g.deadline) - julianday('now') AS INTEGER)
            END AS days_left
        FROM savings_goals g
        LEFT JOIN accounts a ON a.id = g.account_id
        ORDER BY pct_complete DESC
    """).fetchall()


def monthly_savings_rate(conn):
    """Savings rate (net / income) per month."""
    return conn.execute("""
        SELECT
            strftime('%Y-%m', txn_date)  AS month,
            ROUND(SUM(CASE WHEN txn_type='income'  THEN amount ELSE 0 END), 2) AS income,
            ROUND(SUM(CASE WHEN txn_type='expense' THEN amount ELSE 0 END), 2) AS expenses,
            ROUND(
                (SUM(CASE WHEN txn_type='income' THEN amount ELSE 0 END) -
                 SUM(CASE WHEN txn_type='expense' THEN amount ELSE 0 END))
                / NULLIF(SUM(CASE WHEN txn_type='income' THEN amount ELSE 0 END), 0) * 100,
            1)                           AS savings_rate_pct
        FROM transactions
        GROUP BY month
        ORDER BY month
    """).fetchall()


# ─────────────────────────────────────────────
#  RECURRING BILLS
# ─────────────────────────────────────────────

def upcoming_bills(conn, days_ahead=30):
    """Bills due in the next N days."""
    return conn.execute("""
        SELECT
            b.name,
            b.amount,
            b.frequency,
            b.next_due,
            c.name          AS category,
            a.name          AS account,
            CAST(julianday(b.next_due) - julianday('now') AS INTEGER) AS days_until_due
        FROM recurring_bills b
        LEFT JOIN categories c ON c.id = b.category_id
        LEFT JOIN accounts   a ON a.id = b.account_id
        WHERE b.is_active = 1
          AND b.next_due <= date('now', '+' || ? || ' days')
        ORDER BY b.next_due
    """, (days_ahead,)).fetchall()


def annual_recurring_cost(conn):
    """Total annual cost of all recurring bills."""
    return conn.execute("""
        SELECT
            b.name,
            b.amount,
            b.frequency,
            ROUND(b.amount * CASE b.frequency
                WHEN 'weekly'     THEN 52
                WHEN 'monthly'    THEN 12
                WHEN 'quarterly'  THEN 4
                WHEN 'yearly'     THEN 1
            END, 2) AS annual_cost,
            c.name  AS category
        FROM recurring_bills b
        LEFT JOIN categories c ON c.id = b.category_id
        WHERE b.is_active = 1
        ORDER BY annual_cost DESC
    """).fetchall()


# ─────────────────────────────────────────────
#  RECENT TRANSACTIONS
# ─────────────────────────────────────────────

def recent_transactions(conn, limit=20):
    return conn.execute("""
        SELECT
            t.txn_date,
            t.description,
            t.merchant,
            c.name          AS category,
            a.name          AS account,
            t.txn_type,
            t.amount,
            CASE t.txn_type WHEN 'income' THEN '+' ELSE '-' END AS sign
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        JOIN accounts   a ON t.account_id  = a.id
        ORDER BY t.txn_date DESC, t.id DESC
        LIMIT ?
    """, (limit,)).fetchall()


if __name__ == "__main__":
    with get_conn() as conn:
        print("\n=== NET WORTH ===")
        r = net_worth(conn)
        for k in r.keys():
            print(f"  {k:<22} ${r[k]:,.2f}")
