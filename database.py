from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()


# ================= USERS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    solved_challenges = db.relationship('SolvedChallenge', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)

    def get_solved_count(self):
        return len(self.solved_challenges)

    def get_achievements_count(self):
        return UserAchievement.query.filter_by(user_id=self.id).count()

    def get_completed_achievements(self):
        return UserAchievement.query.filter_by(user_id=self.id).all()


# ================= CHALLENGES =================

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), default='easy')

    flag = db.Column(db.String(500), nullable=False)

    hints = db.Column(db.Text)  # JSON строка
    files = db.Column(db.String(500))  # файлы задания (через запятую)

    writeup_filename = db.Column(db.String(200))  # 🔥 ФАЙЛ райтапа

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # связи
    solved_by = db.relationship('SolvedChallenge', backref='challenge', lazy=True)


# ================= ACHIEVEMENTS =================

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)

    icon = db.Column(db.String(50), default='bi-trophy')
    color = db.Column(db.String(20), default='warning')

    # 🔥 логика ачивок
    criteria_type = db.Column(db.String(50))
    criteria_value = db.Column(db.Text)  # JSON

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_achievements = db.relationship('UserAchievement', backref='achievement', lazy=True)

    def get_criteria_display(self):
        if not self.criteria_value:
            return "Особая ачивка"

        try:
            criteria = json.loads(self.criteria_value)
        except:
            return "Особая ачивка"

        if self.criteria_type == 'solve_count':
            return f"Решить {criteria.get('count', 1)} заданий"

        elif self.criteria_type == 'category_solve':
            return f"Решить {criteria.get('count', 1)} заданий категории {criteria.get('category')}"

        return "Особая ачивка"


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'))
    obtained_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================= SOLVES =================

class SolvedChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)

    solved_at = db.Column(db.DateTime, default=datetime.utcnow)
    attempts = db.Column(db.Integer, default=0)


# ================= HINTS =================

class UserHint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)

    hint_index = db.Column(db.Integer, nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================= FLAG LOGS =================

class FlagLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)

    flag_attempt = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================= WRITEUP ACCESS =================

class UserWriteupAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)

    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)