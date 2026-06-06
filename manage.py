"""
manage.py — Interactive CLI to add transactions, manage accounts, and track goals.
Usage: python manage.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from queries import get_conn, net_worth, account_balances, upcoming_bills, savings_goals_progress

# ── Helpers ───────────────────────────────────────────────────────────────────

def prompt(msg, default=None):
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"  {msg}{suffix}: ").strip()
    return val if val else default

def confirm(msg):
    return input(f"  {msg} (y/n): ").strip().lower() == "y"

def hr():
    print("─" * 62)

def menu(title, options):
    print(f"\n{'─'*62}")
    print(f"  {title}")
    print("─"*62)
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print("  0. Back / Exit")
    print("─"*62)
    try:
        return int(input("  Choice: ").strip())
    except ValueError:
        return -1


# ── Transactions ──────────────────────────────────────────────────────────────

def add_transaction(conn):
    print("\n  ── Add Transaction ──")
    txn_type = prompt("Type (income/expense/transfer)").lower()
    if txn_type not in ("income","expense","transfer"):
        print("  ❌  Invalid type."); return

    # Pick account
    accounts = conn.execute("SELECT id,name,type,balance FROM accounts WHERE is_active=1").fetchall()
    print("\n  Accounts:")
    for a in accounts:
        print(f"    {a['id']}. {a['name']}  (${a['balance']:,.2f})")
    acct_id = int(prompt("Account ID"))

    # Pick category
    cat_type = "income" if txn_type == "income" else "expense"
    cats = conn.execute("SELECT id,name FROM categories WHERE type=?", (cat_type,)).fetchall()
    print(f"\n  {cat_type.title()} Categories:")
    for c in cats:
        print(f"    {c['id']}. {c['name']}")
    cat_id = int(prompt("Category ID"))

    amount      = float(prompt("Amount (positive number)"))
    description = prompt("Description", "")
    merchant    = prompt("Merchant / payee", "")
    date_str    = prompt("Date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
    recurring   = 1 if prompt("Recurring? (y/n)", "n").lower() == "y" else 0

    print(f"\n  {txn_type.upper()}  ${amount:,.2f}  —  {description or '(no desc)'}  [{date_str}]")
    if confirm("Save?"):
        conn.execute("""
            INSERT INTO transactions
              (account_id,category_id,amount,txn_type,description,merchant,txn_date,is_recurring)
            VALUES(?,?,?,?,?,?,?,?)
        """, (acct_id, cat_id, amount, txn_type, description or None,
              merchant or None, date_str, recurring))

        # Update account balance
        if txn_type == "income":
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id=?", (amount, acct_id))
        else:
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id=?", (amount, acct_id))

        conn.commit()
        print("  ✅  Transaction saved.")


def list_recent(conn, n=15):
    rows = conn.execute("""
        SELECT t.txn_date, t.description, t.merchant, c.name AS cat,
               a.name AS acct, t.txn_type, t.amount
        FROM transactions t
        JOIN categories c ON t.category_id=c.id
        JOIN accounts   a ON t.account_id=a.id
        ORDER BY t.txn_date DESC, t.id DESC
        LIMIT ?
    """, (n,)).fetchall()

    print(f"\n  {'Date':<12}  {'Description':<22}  {'Category':<18}  {'Account':<20}  {'Amount':>10}")
    hr()
    for r in rows:
        sign = "+" if r["txn_type"] == "income" else "-"
        desc = (r["description"] or r["merchant"] or "")[:21]
        print(f"  {r['txn_date']:<12}  {desc:<22}  {r['cat']:<18}  "
              f"{r['acct']:<20}  {sign}${r['amount']:>9,.2f}")


def search_transactions(conn):
    term = prompt("Search keyword (description/merchant)").lower()
    rows = conn.execute("""
        SELECT t.txn_date, t.description, t.merchant, c.name AS cat,
               t.txn_type, t.amount
        FROM transactions t JOIN categories c ON t.category_id=c.id
        WHERE LOWER(t.description) LIKE ? OR LOWER(t.merchant) LIKE ?
        ORDER BY t.txn_date DESC LIMIT 30
    """, (f"%{term}%", f"%{term}%")).fetchall()

    if not rows:
        print("  No results found."); return
    total = sum(r["amount"] for r in rows)
    print(f"\n  Found {len(rows)} transactions  (total: ${total:,.2f})\n")
    for r in rows:
        sign = "+" if r["txn_type"] == "income" else "-"
        desc = (r["description"] or "")[:20]
        merch = (r["merchant"] or "")[:16]
        print(f"  {r['txn_date']}  {desc:<20}  {merch:<16}  {r['cat']:<18}  {sign}${r['amount']:>9,.2f}")


# ── Accounts ──────────────────────────────────────────────────────────────────

def add_account(conn):
    print("\n  ── Add Account ──")
    name    = prompt("Account name")
    atype   = prompt("Type (checking/savings/credit/investment/cash)").lower()
    balance = float(prompt("Opening balance", 0))
    if confirm(f"Add '{name}' ({atype}) with balance ${balance:,.2f}?"):
        conn.execute("INSERT INTO accounts(name,type,balance) VALUES(?,?,?)", (name, atype, balance))
        conn.commit()
        print("  ✅  Account added.")


def update_account_balance(conn):
    accounts = conn.execute("SELECT id,name,balance FROM accounts WHERE is_active=1").fetchall()
    print("\n  Accounts:")
    for a in accounts:
        print(f"    {a['id']}. {a['name']}  (${a['balance']:,.2f})")
    acct_id = int(prompt("Account ID to update"))
    new_bal = float(prompt("New balance"))
    if confirm(f"Set balance to ${new_bal:,.2f}?"):
        conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_bal, acct_id))
        conn.commit()
        print("  ✅  Balance updated.")


# ── Savings Goals ─────────────────────────────────────────────────────────────

def add_savings_goal(conn):
    print("\n  ── Add Savings Goal ──")
    name   = prompt("Goal name")
    target = float(prompt("Target amount"))
    saved  = float(prompt("Already saved", 0))
    deadline = prompt("Deadline (YYYY-MM-DD) or leave blank", "")
    accounts = conn.execute("SELECT id,name FROM accounts WHERE is_active=1").fetchall()
    print("  Link to account:")
    for a in accounts: print(f"    {a['id']}. {a['name']}")
    acct_id = int(prompt("Account ID"))
    if confirm(f"Add goal '{name}' (${target:,.2f})?"):
        conn.execute("""
            INSERT INTO savings_goals(name,target_amount,saved_amount,deadline,account_id)
            VALUES(?,?,?,?,?)
        """, (name, target, saved, deadline or None, acct_id))
        conn.commit()
        print("  ✅  Goal added.")


def update_savings_goal(conn):
    rows = savings_goals_progress(conn)
    print("\n  Current Goals:")
    for r in rows:
        print(f"    → {r['name']}  ${r['saved_amount']:,.2f} / ${r['target_amount']:,.2f}  ({r['pct_complete']:.0f}%)")
    name    = prompt("Goal name to update")
    row     = conn.execute("SELECT id, saved_amount FROM savings_goals WHERE name LIKE ?", (f"%{name}%",)).fetchone()
    if not row:
        print("  ❌  Goal not found."); return
    new_amt = float(prompt(f"New saved amount (currently ${row['saved_amount']:,.2f})"))
    conn.execute("UPDATE savings_goals SET saved_amount=?, is_complete=? WHERE id=?",
                 (new_amt, 1 if new_amt >= conn.execute(
                     "SELECT target_amount FROM savings_goals WHERE id=?", (row["id"],)
                 ).fetchone()[0] else 0, row["id"]))
    conn.commit()
    print("  ✅  Goal updated.")


# ── Quick Views ───────────────────────────────────────────────────────────────

def quick_snapshot(conn):
    r = net_worth(conn)
    print(f"""
  ┌──────────────────────────────────────────────┐
  │           FINANCIAL SNAPSHOT                 │
  ├──────────────────────────────────────────────┤
  │  Total Assets        ${r['total_assets']:>20,.2f} │
  │  Total Liabilities   ${r['total_liabilities']:>20,.2f} │
  │  ─────────────────────────────────────────── │
  │  NET WORTH           ${r['net_worth']:>20,.2f} │
  └──────────────────────────────────────────────┘""")

    print("\n  Account Balances:")
    for a in account_balances(conn):
        sign = "-" if a["balance"] < 0 else " "
        print(f"    {a['name']:<24} {a['type']:<12} {sign}${abs(a['balance']):>10,.2f}")


def quick_bills(conn):
    rows = upcoming_bills(conn, 30)
    if not rows:
        print("\n  ✅  No bills due in the next 30 days.")
        return
    total = sum(r["amount"] for r in rows)
    print(f"\n  📆  {len(rows)} bill(s) due in next 30 days  (total: ${total:,.2f})\n")
    for r in rows:
        print(f"    {r['next_due']}  {r['name']:<22}  ${r['amount']:>8,.2f}  ({r['days_until_due']}d)")


# ── Main Loop ─────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═"*62)
    print("   PERSONAL FINANCE & BUDGET TRACKER")
    print("═"*62)

    with get_conn() as conn:
        while True:
            choice = menu("MAIN MENU", [
                "Add transaction",
                "View recent transactions",
                "Search transactions",
                "Add / update account balance",
                "Add account",
                "Add savings goal",
                "Update savings goal progress",
                "Quick: financial snapshot",
                "Quick: upcoming bills",
                "Run full analysis  (calls analyze.py)",
            ])

            if choice == 0:
                print("\n  Goodbye! 💸\n"); break
            elif choice == 1:
                add_transaction(conn)
            elif choice == 2:
                list_recent(conn)
            elif choice == 3:
                search_transactions(conn)
            elif choice == 4:
                update_account_balance(conn)
            elif choice == 5:
                add_account(conn)
            elif choice == 6:
                add_savings_goal(conn)
            elif choice == 7:
                update_savings_goal(conn)
            elif choice == 8:
                quick_snapshot(conn)
            elif choice == 9:
                quick_bills(conn)
            elif choice == 10:
                import analyze; analyze.run_all()
            else:
                print("  Invalid choice.")


if __name__ == "__main__":
    main()
