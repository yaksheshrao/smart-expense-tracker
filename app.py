from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import sqlite3
from datetime import date
from utils.budget import check_budget_alerts
from utils.export import export_to_csv

app = Flask(__name__)
app.secret_key = 'secret-key-change-in-production'
DATABASE = 'expenses.db'

CATEGORIES = [
    'Food & Dining', 'Transport', 'Housing & Rent',
    'Entertainment', 'Healthcare', 'Shopping',
    'Education', 'Utilities', 'Travel', 'Other'
]


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,
        monthly_limit REAL NOT NULL
    )''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    conn = get_db()
    category_filter = request.args.get('category', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = 'SELECT * FROM expenses WHERE 1=1'
    params = []
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    query += ' ORDER BY date DESC'

    expenses = conn.execute(query, params).fetchall()
    total = sum(e['amount'] for e in expenses)
    category_totals = conn.execute(
        'SELECT category, SUM(amount) as total FROM expenses GROUP BY category'
    ).fetchall()
    budgets = conn.execute('SELECT * FROM budgets').fetchall()
    alerts = check_budget_alerts(conn, budgets)
    conn.close()

    return render_template('index.html',
        expenses=expenses, total=total, category_totals=category_totals,
        categories=CATEGORIES, alerts=alerts,
        selected_category=category_filter, start_date=start_date, end_date=end_date)


@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        amount = request.form.get('amount')
        category = request.form.get('category')
        description = request.form.get('description', '')
        expense_date = request.form.get('date', date.today().isoformat())

        if not amount or not category:
            flash('Amount and category are required!', 'danger')
            return render_template('add_expense.html', categories=CATEGORIES)
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid positive amount!', 'danger')
            return render_template('add_expense.html', categories=CATEGORIES)

        conn = get_db()
        conn.execute('INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)',
                     (amount, category, description, expense_date))
        conn.commit()
        conn.close()
        flash(f'Expense of {amount:.2f} added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_expense.html', categories=CATEGORIES, today=date.today().isoformat())


@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    flash('Expense deleted.', 'info')
    return redirect(url_for('index'))


@app.route('/reports')
def reports():
    conn = get_db()
    category_totals = conn.execute(
        'SELECT category, SUM(amount) as total FROM expenses GROUP BY category ORDER BY total DESC'
    ).fetchall()
    monthly_totals = conn.execute(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM expenses GROUP BY month ORDER BY month"
    ).fetchall()
    conn.close()
    return render_template('reports.html', category_totals=category_totals, monthly_totals=monthly_totals)


@app.route('/budget', methods=['GET', 'POST'])
def budget():
    conn = get_db()
    if request.method == 'POST':
        for category in CATEGORIES:
            limit = request.form.get(f'budget_{category}')
            if limit:
                try:
                    conn.execute('INSERT OR REPLACE INTO budgets (category, monthly_limit) VALUES (?, ?)',
                                 (category, float(limit)))
                except ValueError:
                    pass
        conn.commit()
        flash('Budgets updated successfully!', 'success')
        return redirect(url_for('budget'))

    budgets = {b['category']: b['monthly_limit'] for b in conn.execute('SELECT * FROM budgets').fetchall()}
    conn.close()
    return render_template('budget.html', categories=CATEGORIES, budgets=budgets)


@app.route('/export')
def export():
    conn = get_db()
    expenses = conn.execute('SELECT * FROM expenses ORDER BY date DESC').fetchall()
    conn.close()
    output = export_to_csv(expenses)
    response = make_response(output)
    response.headers['Content-Disposition'] = 'attachment; filename=expenses.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
