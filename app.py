from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, bcrypt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
    db.init_app(app)
    bcrypt.init_app(app)

    from models import User, Expense  # Ensure models are imported after db.init_app
    with app.app_context():
        db.create_all()

    from routes import auth_bp, expense_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(expense_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
