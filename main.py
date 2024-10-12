from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict
import jwt
from flask_bcrypt import Bcrypt
from functools import wraps

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:jkf&&%_f3#DF45@127.0.0.1/expenses_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

app.config['SECRET_KEY'] = 'd3c1f01a3bdf44b8a6c993e752a4f407'


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()


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

    return {
        date_key: {
            'category_map': dict(date_info['category_map']),
            'total': date_info['total']
        }
        for date_key, date_info in result_map.items()
    }


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'message': 'User already exists'}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user': username,
        'exp': datetime.utcnow() + timedelta(minutes=30)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token})


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            bearer = request.headers['Authorization']
            token = bearer.split()[1]

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except Exception:
            return jsonify({'message': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated


@app.route('/get-expenses', methods=['GET'])
@token_required
def get_expenses(current_user):
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
            group_by = 'day'
        elif period == 'monthly':
            start_date = today.replace(month=1, day=1)
            end_date = today
            group_by = 'month'
        else:
            return jsonify({'error': 'Invalid period specified'}), 400

        expenses = filter_expenses(str(start_date), str(end_date), category)
        aggregated_data = process(expenses, group_by=group_by)

        return jsonify(aggregated_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/add-expense', methods=['POST'])
@token_required
def add_expense(current_user):
    try:
        data = request.get_json()
        category = data.get('category')
        amount = data.get('amount')
        date_str = data.get('date')
        description = data.get('description', '')

        expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        new_expense = Expense(
            category=category,
            amount=float(amount),
            date=expense_date,
            description=description
        )

        db.session.add(new_expense)
        db.session.commit()

        return jsonify({'message': 'Expense added successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
