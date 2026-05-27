import csv
import io
from datetime import datetime


def export_to_csv(expenses):
    """
    Convert a list of expense rows to CSV format.
    Returns a string containing the CSV data.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['ID', 'Amount', 'Category', 'Description', 'Date', 'Created At'])

    # Write data rows
    for expense in expenses:
        writer.writerow([
            expense['id'],
            f"{expense['amount']:.2f}",
            expense['category'],
            expense['description'] or '',
            expense['date'],
            expense['created_at']
        ])

    return output.getvalue()


def import_from_csv(file_content, conn):
    """
    Import expenses from a CSV file content string.
    Returns (success_count, error_count, errors).
    """
    reader = csv.DictReader(io.StringIO(file_content))
    success_count = 0
    error_count = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            amount = float(row.get('Amount', '').strip())
            category = row.get('Category', '').strip()
            description = row.get('Description', '').strip()
            date_str = row.get('Date', '').strip()

            # Validate date format
            datetime.strptime(date_str, '%Y-%m-%d')

            if not category:
                raise ValueError('Category is required')
            if amount <= 0:
                raise ValueError('Amount must be positive')

            conn.execute(
                'INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)',
                (amount, category, description, date_str)
            )
            success_count += 1

        except (ValueError, KeyError) as e:
            error_count += 1
            errors.append(f'Row {i}: {str(e)}')

    conn.commit()
    return success_count, error_count, errors


def generate_report_csv(conn, start_date=None, end_date=None):
    """
    Generate a summary report CSV with category totals.
    """
    query = 'SELECT category, SUM(amount) as total, COUNT(*) as count FROM expenses'
    params = []

    conditions = []
    if start_date:
        conditions.append('date >= ?')
        params.append(start_date)
    if end_date:
        conditions.append('date <= ?')
        params.append(end_date)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' GROUP BY category ORDER BY total DESC'

    rows = conn.execute(query, params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Category', 'Total Amount', 'Transaction Count', 'Average Amount'])

    for row in rows:
        avg = row['total'] / row['count'] if row['count'] > 0 else 0
        writer.writerow([
            row['category'],
            f"{row['total']:.2f}",
            row['count'],
            f"{avg:.2f}"
        ])

    return output.getvalue()
