# Personal Finance & Budget Tracker — Python + SQLite

A complete personal finance analysis system with zero external dependencies.

---

## Project Structure

```
budget_tracker/
├── data/
│   └── budget.db           ← SQLite database (auto-created)
├── reports/                ← CSV exports land here
├── setup_db.py             ← Create & seed the database
├── queries.py              ← All SQL queries as reusable Python functions
├── analyze.py              ← Full formatted report in the terminal
├── manage.py               ← Interactive CLI (add transactions, goals, etc.)
├── export_reports.py       ← Export all analyses to CSV files
└── README.md
```

---

## Quick Start

> **Requirements**: Python 3.8+. No external packages needed.

```bash
python setup_db.py        # Step 1: create DB and seed sample data
python analyze.py         # Step 2: view full analysis report
python manage.py          # Step 3: add your own data interactively
python export_reports.py  # Step 4: export CSVs for Excel / Sheets
```

---

## What Gets Analyzed

| Report | Description |
|---|---|
| Net Worth | Assets vs liabilities, balance per account |
| Monthly Cashflow | Income, expenses, and net per month |
| Budget vs Actual | How each spending category tracks against its budget |
| Spending by Category | Total and average per income/expense category |
| Savings Rate | Monthly % of income saved, with trend |
| Savings Goals | Progress bars toward each goal with days remaining |
| Top Merchants | Where the most money is being spent |
| Recurring Bills | Annual cost of subscriptions and bills |
| Upcoming Bills | Bills due in next 30 days |
| Weekday vs Weekend | Spending pattern by day type |
| Recurring vs Discretionary | Fixed costs vs flexible spending |
| Recent Transactions | Last 20 transactions across all accounts |

---

## Database Schema

### `accounts`
Tracks balances across checking, savings, credit, investment, and cash accounts.

### `categories`
Income and expense categories, each with an optional monthly budget amount.

### `transactions`
Every financial transaction — income, expense, or transfer — linked to an account and category.

| Field | Description |
|---|---|
| txn_type | `income`, `expense`, or `transfer` |
| amount | Always positive; sign is determined by txn_type |
| is_recurring | 1 = regular bill, 0 = one-off purchase |

### `monthly_budgets`
Per-category budget targets for each calendar month (overrides the category default).

### `savings_goals`
Named goals with a target amount, current saved amount, and optional deadline.

### `recurring_bills`
Subscription and bill tracker with frequency (`weekly`, `monthly`, `quarterly`, `yearly`) and next due date.

---

## Key SQL Concepts Used

- `CASE WHEN` — computing net cashflow, day-type buckets, sign indicators
- `strftime()` — grouping by month, extracting day-of-week
- `COALESCE` / `NULLIF` — safe fallbacks for null budgets and division
- `julianday()` — calculating days until a deadline or bill due date
- `LEFT JOIN` — including categories with no transactions in budget reports
- `GROUP BY` + `SUM` / `AVG` / `COUNT` — all aggregation reports
- `WITH` (CTEs) — not used here but easy to add for rolling averages
- `CHECK` constraints — enforcing valid account types, transaction types, frequencies

---

## Customising

- **Change budget amounts**: edit `monthly_budgets` table or update `categories.monthly_budget`
- **Add a new category**: insert into `categories`, then tag transactions to it
- **Add a report**: write a function in `queries.py`, call it in `analyze.py` and `export_reports.py`
- **Use real data**: replace seed data in `setup_db.py`; schema stays the same
- **Switch to PostgreSQL**: swap `sqlite3.connect()` for `psycopg2.connect()` — all SQL is standard
