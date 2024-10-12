from functools import wraps
from flask import request, jsonify
import jwt
from datetime import datetime
from collections import defaultdict
from typing import Dict
from models import Expense
from config import Config

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
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = data['user']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except Exception:
            return jsonify({'message': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

def filter_expenses(start_date, end_date, category=None):
    query = Expense.query.filter(Expense.date.between(start_date, end_date))
    if category:
        query = query.filter_by(category=category)
    return query.all()

def process(data_list, group_by='day', all_categories=None) -> Dict[str, Dict]:
    result_map = defaultdict(lambda: {'category_map': defaultdict(float), 'total': 0.0})

    for data in data_list:
        if group_by == 'day':
            date_key = data.date.strftime('%Y-%m-%d')
        elif group_by == 'month':
            date_key = data.date.strftime('%Y-%m')
        else:
            date_key = data.date.strftime('%Y-%m-%d')

        category = data.category
        amount = data.amount

        date_info = result_map[date_key]
        date_info['category_map'][category] += amount
        date_info['total'] += amount

    # Include all categories with zero amounts if they are not present
    if all_categories is not None:
        for date_info in result_map.values():
            for category in all_categories:
                date_info['category_map'].setdefault(category, 0.0)

    return {
        date_key: {
            'category_map': dict(date_info['category_map']),
            'total': date_info['total']
        }
        for date_key, date_info in result_map.items()
    }
