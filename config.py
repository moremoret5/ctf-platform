import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///ctf.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Challenge categories
    CATEGORIES = [
        'stego', 'forensic', 'pwn', 'revers',
        'osint', 'web', 'joy', 'crypto'
    ]

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Admin settings
    ADMIN_USERNAMES = ['admin']  # Initial admin user