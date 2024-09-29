from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
from collections import defaultdict
from typing import List, Dict

app = Flask(__name__)
CORS(app)

# MySQL Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:jkf&&%_f3#DF45@127.0.0.1/expenses_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the Expense model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200))

# Create the database tables (if they don't exist)
with app.app_context():
    db.create_all()

# Helper function to filter expenses by date range and category
def filter_expenses(start_date, end_date, category=None):
    query = Expense.query.filter(Expense.date.between(start_date, end_date))
    if category:
        query = query.filter_by(category=category)
    return query.all()

def process(data_list, group_by='day') -> Dict[str, Dict]:
    result_map = defaultdict(lambda: {'category_map': defaultdict(float), 'total': 0.0})

    for data in data_list:
        if group_by == 'day':
            date_key = data.date.strftime('%Y-%m-%d')
        elif group_by == 'week':
            year, week_num, _ = data.date.isocalendar()
            date_key = f'{year}-W{week_num:02d}'
        elif group_by == 'month':
            date_key = data.date.strftime('%Y-%m')
        else:
            date_key = data.date.strftime('%Y-%m-%d')

        category = data.category
        amount = data.amount

        date_info = result_map[date_key]
        date_info['category_map'][category] += amount
        date_info['total'] += amount

    # Convert defaultdicts to regular dicts for JSON serialization
    return {
        date_key: {
            'category_map': dict(date_info['category_map']),
            'total': date_info['total']
        }
        for date_key, date_info in result_map.items()
    }

@app.route('/add-expense', methods=['POST'])
def add_expense():
    try:
        data = request.get_json()
        category = data.get('category')
        amount = data.get('amount')
        date_str = data.get('date')
        description = data.get('description', '')

        # Convert date to the appropriate format
        expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Create a new Expense instance
        new_expense = Expense(
            category=category,
            amount=float(amount),
            date=expense_date,
            description=description
        )

        # Add the new expense to the database
        db.session.add(new_expense)
        db.session.commit()

        return jsonify({'message': 'Expense added successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/get-expenses', methods=['GET'])
def get_expenses():
    try:
        period = request.args.get('period', 'daily')
        category = request.args.get('category', None)
        today = datetime.today().date()

        if period == 'daily':
            start_date = today.replace(day=1)
            end_date = today
            group_by = 'day'
        elif period == 'weekly':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
            group_by = 'day'  # You can change this to 'week' if you want weekly aggregation
        elif period == 'monthly':
            start_date = today.replace(month=1, day=1)
            end_date = today
            group_by = 'month'
        else:
            return jsonify({'error': 'Invalid period specified'}), 400

        # Fetch expenses within the given date range and optional category
        expenses = filter_expenses(str(start_date), str(end_date), category)
        aggregated_data = process(expenses, group_by=group_by)

        return jsonify(aggregated_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
