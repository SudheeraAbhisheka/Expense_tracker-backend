from flask import Blueprint, request, jsonify
from models import User, Expense
from utils import filter_expenses, process, token_required
from extensions import db, bcrypt
import jwt
from datetime import datetime, timedelta
from config import Config

auth_bp = Blueprint('auth_bp', __name__)
expense_bp = Blueprint('expense_bp', __name__)

CATEGORIES = ["Food", "Travel", "Entertainment", "Health", "Other"]

@auth_bp.route('/register', methods=['POST'])
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

@auth_bp.route('/login', methods=['POST'])
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
    }, Config.SECRET_KEY, algorithm='HS256')

    return jsonify({'token': token})

@expense_bp.route('/get-expenses', methods=['GET'])
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
        elif period == 'monthly':
            start_date = today.replace(month=1, day=1)
            end_date = today
            group_by = 'month'
        else:
            return jsonify({'error': 'Invalid period specified'}), 400

        expenses = filter_expenses(str(start_date), str(end_date), category)

        # Pass all_categories when no specific category is selected
        if not category:
            aggregated_data = process(expenses, group_by=group_by, all_categories=CATEGORIES)
        else:
            aggregated_data = process(expenses, group_by=group_by)

        return jsonify(aggregated_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@expense_bp.route('/add-expense', methods=['POST'])
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
