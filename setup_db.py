"""
setup_db.py — Creates and seeds the budget/finance SQLite database.
Run this first: python setup_db.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/budget.db")


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def create_tables(conn):
    conn.executescript("""
        -- Accounts (checking, savings, credit card, etc.)
        CREATE TABLE IF NOT EXISTS accounts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            type         TEXT NOT NULL CHECK(type IN ('checking','savings','credit','investment','cash')),
            balance      REAL NOT NULL DEFAULT 0,
            currency     TEXT NOT NULL DEFAULT 'USD',
            is_active    INTEGER NOT NULL DEFAULT 1,
            opened_date  TEXT NOT NULL DEFAULT (date('now'))
        );

        -- Budget categories
        CREATE TABLE IF NOT EXISTS categories (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            type         TEXT NOT NULL CHECK(type IN ('income','expense')),
            monthly_budget REAL DEFAULT NULL,
            color        TEXT DEFAULT '#888888'
        );

        -- Transactions
        CREATE TABLE IF NOT EXISTS transactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id   INTEGER NOT NULL REFERENCES accounts(id),
            category_id  INTEGER REFERENCES categories(id),
            amount       REAL NOT NULL,
            txn_type     TEXT NOT NULL CHECK(txn_type IN ('income','expense','transfer')),
            description  TEXT,
            merchant     TEXT,
            txn_date     TEXT NOT NULL DEFAULT (date('now')),
            is_recurring INTEGER NOT NULL DEFAULT 0
        );

        -- Monthly budgets (per category per month)
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id  INTEGER NOT NULL REFERENCES categories(id),
            year_month   TEXT NOT NULL,   -- e.g. '2026-03'
            budget_amt   REAL NOT NULL,
            UNIQUE(category_id, year_month)
        );

        -- Savings goals
        CREATE TABLE IF NOT EXISTS savings_goals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount  REAL NOT NULL DEFAULT 0,
            deadline      TEXT,
            account_id    INTEGER REFERENCES accounts(id),
            is_complete   INTEGER NOT NULL DEFAULT 0
        );

        -- Recurring bills
        CREATE TABLE IF NOT EXISTS recurring_bills (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            amount       REAL NOT NULL,
            category_id  INTEGER REFERENCES categories(id),
            account_id   INTEGER REFERENCES accounts(id),
            frequency    TEXT NOT NULL CHECK(frequency IN ('weekly','monthly','quarterly','yearly')),
            next_due     TEXT NOT NULL,
            is_active    INTEGER NOT NULL DEFAULT 1
        );
    """)
    conn.commit()
    print("✅  Tables created.")


def seed_data(conn):
    cur = conn.cursor()

    # --- Accounts ---
    accounts = [
        ("Main Checking",   "checking",   4250.00),
        ("High-Yield Savings","savings",  12800.00),
        ("Visa Credit Card","credit",     -1340.00),
        ("Investment Account","investment",28500.00),
        ("Cash Wallet",     "cash",         180.00),
    ]
    for name, atype, bal in accounts:
        cur.execute(
            "INSERT OR IGNORE INTO accounts(name,type,balance) VALUES(?,?,?)",
            (name, atype, bal)
        )

    # --- Categories ---
    categories = [
        # income
        ("Salary",          "income",  5500.00, "#27ae60"),
        ("Freelance",       "income",   800.00, "#2ecc71"),
        ("Investment Returns","income", 200.00, "#1abc9c"),
        ("Other Income",    "income",   100.00, "#16a085"),
        # expense
        ("Housing",         "expense", 1400.00, "#e74c3c"),
        ("Groceries",       "expense",  400.00, "#e67e22"),
        ("Transport",       "expense",  200.00, "#f39c12"),
        ("Utilities",       "expense",  150.00, "#d35400"),
        ("Dining Out",      "expense",  250.00, "#c0392b"),
        ("Entertainment",   "expense",  100.00, "#9b59b6"),
        ("Healthcare",      "expense",  100.00, "#3498db"),
        ("Clothing",        "expense",  100.00, "#2980b9"),
        ("Subscriptions",   "expense",   80.00, "#8e44ad"),
        ("Travel",          "expense",  200.00, "#2c3e50"),
        ("Education",       "expense",   50.00, "#34495e"),
        ("Savings Transfer","expense",  500.00, "#7f8c8d"),
        ("Miscellaneous",   "expense",   80.00, "#95a5a6"),
    ]
    for name, ctype, budget, color in categories:
        cur.execute(
            "INSERT OR IGNORE INTO categories(name,type,monthly_budget,color) VALUES(?,?,?,?)",
            (name, ctype, budget, color)
        )
    conn.commit()

    acc  = {r[0]: r[1] for r in cur.execute("SELECT name,id FROM accounts")}
    cat  = {r[0]: r[1] for r in cur.execute("SELECT name,id FROM categories")}

    # --- Monthly budgets for last 6 months ---
    today = datetime.now()
    months = [(today - timedelta(days=30*i)).strftime("%Y-%m") for i in range(6)]
    for ym in months:
        for name, ctype, budget, _ in categories:
            if budget:
                cur.execute("""
                    INSERT OR IGNORE INTO monthly_budgets(category_id,year_month,budget_amt)
                    VALUES(?,?,?)
                """, (cat[name], ym, budget))
    conn.commit()

    # --- Transactions (past 6 months) ---
    random.seed(99)
    base = datetime.now() - timedelta(days=180)
    txns = []

    # Recurring salary every month
    for m in range(6):
        d = (base + timedelta(days=30*m + 1)).strftime("%Y-%m-%d")
        txns.append((acc["Main Checking"], cat["Salary"], 5500.00, "income",
                     "Monthly salary", "Employer Corp", d, 1))

    # Freelance (irregular)
    for m in range(6):
        if random.random() > 0.35:
            d = (base + timedelta(days=30*m + random.randint(5,20))).strftime("%Y-%m-%d")
            amt = round(random.uniform(300, 1200), 2)
            txns.append((acc["Main Checking"], cat["Freelance"], amt, "income",
                         "Freelance project", "Client", d, 0))

    # Investment returns
    for m in range(6):
        if random.random() > 0.4:
            d = (base + timedelta(days=30*m + random.randint(1,28))).strftime("%Y-%m-%d")
            amt = round(random.uniform(50, 450), 2)
            txns.append((acc["Investment Account"], cat["Investment Returns"], amt, "income",
                         "Dividends / returns", "Broker", d, 0))

    # Recurring rent
    for m in range(6):
        d = (base + timedelta(days=30*m + 1)).strftime("%Y-%m-%d")
        txns.append((acc["Main Checking"], cat["Housing"], 1350.00, "expense",
                     "Monthly rent", "Landlord LLC", d, 1))

    # Groceries (weekly-ish)
    grocery_stores = ["Whole Foods", "Trader Joe's", "Kroger", "Costco", "Aldi"]
    for m in range(6):
        for w in range(4):
            d = (base + timedelta(days=30*m + 7*w + random.randint(0,3))).strftime("%Y-%m-%d")
            amt = round(random.uniform(45, 140), 2)
            txns.append((acc["Main Checking"], cat["Groceries"], amt, "expense",
                         "Weekly groceries", random.choice(grocery_stores), d, 0))

    # Dining out
    restaurants = ["Chipotle","Starbucks","Pizza Hut","Subway","Local Bistro","Sushi Place"]
    for m in range(6):
        for _ in range(random.randint(4, 10)):
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(8, 75), 2)
            txns.append((acc["Visa Credit Card"], cat["Dining Out"], amt, "expense",
                         "Dining out", random.choice(restaurants), d, 0))

    # Transport (gas / uber)
    for m in range(6):
        for _ in range(random.randint(3, 7)):
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(15, 65), 2)
            merchant = random.choice(["Shell Gas","BP Station","Uber","Lyft","Metro Card"])
            txns.append((acc["Main Checking"], cat["Transport"], amt, "expense",
                         "Transport", merchant, d, 0))

    # Utilities (monthly)
    for m in range(6):
        d = (base + timedelta(days=30*m + 5)).strftime("%Y-%m-%d")
        amt = round(random.uniform(110, 185), 2)
        txns.append((acc["Main Checking"], cat["Utilities"], amt, "expense",
                     "Utilities bill", "City Power & Gas", d, 1))

    # Subscriptions (monthly)
    subs = [("Netflix", 15.99), ("Spotify", 9.99), ("Gym", 35.00), ("iCloud", 2.99)]
    for m in range(6):
        for name, amt in subs:
            d = (base + timedelta(days=30*m + random.randint(1,5))).strftime("%Y-%m-%d")
            txns.append((acc["Visa Credit Card"], cat["Subscriptions"], amt, "expense",
                         f"{name} subscription", name, d, 1))

    # Entertainment
    for m in range(6):
        for _ in range(random.randint(1, 4)):
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(10, 80), 2)
            merchant = random.choice(["Cinema","Steam","Amazon","Apple Store","Bowling"])
            txns.append((acc["Visa Credit Card"], cat["Entertainment"], amt, "expense",
                         "Entertainment", merchant, d, 0))

    # Healthcare (occasional)
    for m in range(6):
        if random.random() > 0.5:
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(20, 200), 2)
            txns.append((acc["Main Checking"], cat["Healthcare"], amt, "expense",
                         "Healthcare", random.choice(["CVS Pharmacy","Doctor Visit","Dentist"]), d, 0))

    # Clothing (occasional)
    for m in range(6):
        if random.random() > 0.55:
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(25, 180), 2)
            txns.append((acc["Visa Credit Card"], cat["Clothing"], amt, "expense",
                         "Clothing", random.choice(["H&M","Zara","Nike","Uniqlo"]), d, 0))

    # Savings transfers
    for m in range(6):
        d = (base + timedelta(days=30*m + 15)).strftime("%Y-%m-%d")
        txns.append((acc["Main Checking"], cat["Savings Transfer"], 500.00, "expense",
                     "Transfer to savings", "Internal Transfer", d, 1))

    # Travel (sporadic)
    for m in range(6):
        if random.random() > 0.65:
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(80, 600), 2)
            txns.append((acc["Visa Credit Card"], cat["Travel"], amt, "expense",
                         "Travel expense", random.choice(["Airbnb","Delta Airlines","Booking.com","Hotel"]), d, 0))

    # Misc
    for m in range(6):
        for _ in range(random.randint(1, 3)):
            d = (base + timedelta(days=30*m + random.randint(0,29))).strftime("%Y-%m-%d")
            amt = round(random.uniform(5, 60), 2)
            txns.append((acc["Cash Wallet"], cat["Miscellaneous"], amt, "expense",
                         "Misc purchase", "Various", d, 0))

    cur.executemany("""
        INSERT INTO transactions
          (account_id,category_id,amount,txn_type,description,merchant,txn_date,is_recurring)
        VALUES(?,?,?,?,?,?,?,?)
    """, txns)
    conn.commit()

    # --- Savings Goals ---
    goals = [
        ("Emergency Fund",    10000.00,  6500.00, "2026-12-31", acc["High-Yield Savings"]),
        ("Vacation to Japan", 3000.00,   1200.00, "2026-09-01", acc["High-Yield Savings"]),
        ("New Laptop",         1500.00,   900.00, "2026-07-01", acc["High-Yield Savings"]),
        ("House Down Payment",50000.00, 12000.00, "2029-01-01", acc["Investment Account"]),
    ]
    for name, target, saved, deadline, acct_id in goals:
        cur.execute("""
            INSERT OR IGNORE INTO savings_goals(name,target_amount,saved_amount,deadline,account_id)
            VALUES(?,?,?,?,?)
        """, (name, target, saved, deadline, acct_id))

    # --- Recurring Bills ---
    bills = [
        ("Rent",        1350.00, cat["Housing"],       acc["Main Checking"],      "monthly",  "2026-07-01"),
        ("Netflix",       15.99, cat["Subscriptions"], acc["Visa Credit Card"],   "monthly",  "2026-07-05"),
        ("Spotify",        9.99, cat["Subscriptions"], acc["Visa Credit Card"],   "monthly",  "2026-07-05"),
        ("Gym Membership",35.00, cat["Subscriptions"], acc["Visa Credit Card"],   "monthly",  "2026-07-08"),
        ("City Power & Gas",145.00,cat["Utilities"],   acc["Main Checking"],      "monthly",  "2026-07-05"),
        ("Car Insurance", 112.00, cat["Transport"],    acc["Main Checking"],      "monthly",  "2026-07-15"),
        ("iCloud Storage",  2.99, cat["Subscriptions"],acc["Visa Credit Card"],   "monthly",  "2026-07-03"),
        ("Domain/Hosting", 12.00, cat["Subscriptions"],acc["Visa Credit Card"],   "yearly",   "2027-01-01"),
    ]
    for name, amt, cat_id, acct_id, freq, next_due in bills:
        cur.execute("""
            INSERT OR IGNORE INTO recurring_bills(name,amount,category_id,account_id,frequency,next_due)
            VALUES(?,?,?,?,?,?)
        """, (name, amt, cat_id, acct_id, freq, next_due))

    conn.commit()
    print(f"✅  Seeded {len(accounts)} accounts, {len(categories)} categories, "
          f"{len(txns)} transactions, {len(goals)} savings goals, {len(bills)} recurring bills.")


if __name__ == "__main__":
    print("🔧  Setting up budget database...")
    with get_conn() as conn:
        create_tables(conn)
        seed_data(conn)
    print(f"\n🗄️   Database ready at: {DB_PATH.resolve()}")
