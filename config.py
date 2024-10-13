import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'd3c1f01a3bdf44b8a6c993e752a4f407'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'expenses_db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
