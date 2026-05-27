from datetime import datetime


def check_budget_alerts(conn, budgets):
    """
    Check if any category has exceeded or is close to its monthly budget.
    Returns a list of alert dictionaries.
    """
    alerts = []
    current_month = datetime.now().strftime('%Y-%m')

    for budget in budgets:
        category = budget['category']
        monthly_limit = budget['monthly_limit']

        # Get this month's spending for the category
        result = conn.execute(
            """SELECT SUM(amount) as total FROM expenses
               WHERE category = ? AND strftime('%Y-%m', date) = ?""",
            (category, current_month)
        ).fetchone()

        spent = result['total'] or 0.0
        percentage = (spent / monthly_limit * 100) if monthly_limit > 0 else 0

        if percentage >= 100:
            alerts.append({
                'category': category,
                'spent': spent,
                'limit': monthly_limit,
                'percentage': round(percentage, 1),
                'level': 'danger',
                'message': f'{category}: Budget exceeded! Spent {spent:.2f} of {monthly_limit:.2f}'
            })
        elif percentage >= 80:
            alerts.append({
                'category': category,
                'spent': spent,
                'limit': monthly_limit,
                'percentage': round(percentage, 1),
                'level': 'warning',
                'message': f'{category}: {percentage:.0f}% of budget used ({spent:.2f}/{monthly_limit:.2f})'
            })

    return alerts


def get_monthly_summary(conn, year=None, month=None):
    """
    Get spending summary for a given month.
    Defaults to current month if not specified.
    """
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month

    month_str = f'{year:04d}-{month:02d}'

    rows = conn.execute(
        """SELECT category, SUM(amount) as total, COUNT(*) as count
           FROM expenses
           WHERE strftime('%Y-%m', date) = ?
           GROUP BY category
           ORDER BY total DESC""",
        (month_str,)
    ).fetchall()

    return {
        'month': month_str,
        'categories': [dict(r) for r in rows],
        'total': sum(r['total'] for r in rows)
    }
