import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from database import db, User, Challenge, SolvedChallenge, UserHint, FlagLog, UserWriteupAccess, Achievement, \
    UserAchievement

app = Flask(__name__)
app.config.from_object(Config)

# Extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user_login'

# Upload folders
os.makedirs('uploads/challenges', exist_ok=True)
os.makedirs('uploads/writeups', exist_ok=True)
os.makedirs('uploads/achievements', exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'tar', 'gz', 'md', 'html'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_achievement_icon(filename):
    return allowed_file(filename) and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'svg'}


# ================= USER ROUTES =================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('challenges'))
    return render_template('user/index.html')


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for('challenges'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('challenges'))
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('user/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('challenges'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занят', 'danger')
        else:
            is_admin = False
            if not User.query.first() or username in Config.ADMIN_USERNAMES:
                is_admin = True
            user = User(username=username, password=generate_password_hash(password), is_admin=is_admin)
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('user_login'))
    return render_template('user/register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/challenges')
@login_required
def challenges():
    category = request.args.get('category', 'all')
    challenges_query = Challenge.query.filter_by(is_active=True)
    if category != 'all' and category in Config.CATEGORIES:
        challenges_query = challenges_query.filter_by(category=category)
    challenges_list = challenges_query.all()
    solved_ids = [sc.challenge_id for sc in SolvedChallenge.query.filter_by(user_id=current_user.id).all()]
    return render_template('user/challenges.html',
                           challenges=challenges_list,
                           categories=Config.CATEGORIES,
                           selected_category=category,
                           solved_ids=solved_ids)


@app.route('/challenge/<int:challenge_id>', methods=['GET', 'POST'])
@login_required
def challenge_detail(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    if not challenge.is_active and not current_user.is_admin:
        flash('Это задание недоступно', 'danger')
        return redirect(url_for('challenges'))

    solved = SolvedChallenge.query.filter_by(user_id=current_user.id, challenge_id=challenge_id).first()
    unlocked_hints = UserHint.query.filter_by(user_id=current_user.id, challenge_id=challenge_id).order_by(
        UserHint.hint_index).all()

    hints_list = []
    if challenge.hints:
        try:
            hints_data = json.loads(challenge.hints)
            for i, hint in enumerate(hints_data):
                is_unlocked = any(uh.hint_index == i for uh in unlocked_hints)
                hints_list.append({'text': hint, 'unlocked': is_unlocked, 'index': i})
        except:
            pass

    wrong_attempts = FlagLog.query.filter_by(user_id=current_user.id, challenge_id=challenge_id,
                                             is_correct=False).count()

    if request.method == 'POST':
        flag = request.form.get('flag', '').strip()
        log = FlagLog(user_id=current_user.id, challenge_id=challenge_id,
                      flag_attempt=flag, is_correct=(flag == challenge.flag),
                      ip_address=request.remote_addr, user_agent=request.user_agent.string)
        db.session.add(log)

        if flag == challenge.flag:
            if not solved:
                db.session.add(SolvedChallenge(user_id=current_user.id, challenge_id=challenge_id,
                                               attempts=wrong_attempts + 1))
            # Выдача ачивки
            ach = Achievement.query.filter_by(challenge_id=challenge_id).first()
            if ach and not UserAchievement.query.filter_by(user_id=current_user.id, achievement_id=ach.id).first():
                db.session.add(UserAchievement(user_id=current_user.id, achievement_id=ach.id))
                flash(f'🏆 Получена ачивка: {ach.name}!', 'success')

            db.session.commit()
            flash('Правильный флаг! Задание решено!', 'success')
            return redirect(url_for('challenges'))
        else:
            total_wrong = wrong_attempts + 1
            if challenge.hints:
                hints_data = json.loads(challenge.hints)
                for i in range(len(hints_data)):
                    if total_wrong >= (i + 1) * 3:
                        if not UserHint.query.filter_by(user_id=current_user.id, challenge_id=challenge_id,
                                                        hint_index=i).first():
                            db.session.add(UserHint(user_id=current_user.id, challenge_id=challenge_id, hint_index=i))
            db.session.commit()
            flash('Неправильный флаг! Попробуйте еще раз.', 'danger')
            return redirect(url_for('challenge_detail', challenge_id=challenge_id))

    writeup_available = False
    if challenge.hints and wrong_attempts >= len(json.loads(challenge.hints)) * 3:
        writeup_available = True
    writeup_accessed = UserWriteupAccess.query.filter_by(user_id=current_user.id, challenge_id=challenge_id).first()

    return render_template('user/challenge_detail.html', challenge=challenge,
                           solved=solved, hints=hints_list, wrong_attempts=wrong_attempts,
                           writeup_available=writeup_available, writeup_accessed=writeup_accessed)


@app.route('/challenge/<int:challenge_id>/writeup')
@login_required
def view_writeup(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    wrong_attempts = FlagLog.query.filter_by(user_id=current_user.id, challenge_id=challenge_id,
                                             is_correct=False).count()
    if challenge.hints and wrong_attempts < len(json.loads(challenge.hints)) * 3 and not current_user.is_admin:
        flash('Доступ к райтапу пока недоступен. Сделайте больше попыток.', 'warning')
        return redirect(url_for('challenge_detail', challenge_id=challenge_id))

    if not UserWriteupAccess.query.filter_by(user_id=current_user.id, challenge_id=challenge_id).first():
        db.session.add(UserWriteupAccess(user_id=current_user.id, challenge_id=challenge_id))
        db.session.commit()

    return redirect(url_for('download_writeup', filename=challenge.writeup_filename))


@app.route('/writeups')
@login_required
def my_writeups():
    access_records = UserWriteupAccess.query.filter_by(user_id=current_user.id).all()
    writeups_list = []
    for rec in access_records:
        ch = Challenge.query.get(rec.challenge_id)
        if ch and ch.writeup_filename:
            writeups_list.append({'challenge': ch, 'filename': ch.writeup_filename, 'category': ch.category})
    return render_template('user/writeups.html', writeups=writeups_list)


@app.route('/achievements')
@login_required
def my_achievements():
    earned = db.session.query(UserAchievement, Achievement).join(Achievement).filter(
        UserAchievement.user_id == current_user.id
    ).order_by(UserAchievement.obtained_at.desc()).all()  # ← obtained_at как в БД
    all_achievements = Achievement.query.all()
    earned_ids = [ua.achievement_id for ua, _ in earned]
    return render_template('user/achievements.html', earned=earned, all_achievements=all_achievements, earned_ids=earned_ids)


@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory('uploads/challenges', filename)


@app.route('/download_writeup/<path:filename>')
@login_required
def download_writeup(filename):
    return send_from_directory('uploads/writeups', filename)


@app.route('/profile')
@login_required
def profile():
    solved = SolvedChallenge.query.filter_by(user_id=current_user.id).all()
    solved_challenges = [Challenge.query.get(sc.challenge_id) for sc in solved if Challenge.query.get(sc.challenge_id)]
    category_stats = {cat: 0 for cat in Config.CATEGORIES}
    for challenge in solved_challenges:
        if challenge and challenge.category in category_stats:
            category_stats[challenge.category] += 1
    total_points = sum(challenge.points for challenge in solved_challenges if challenge)
    total_active_challenges = Challenge.query.filter_by(is_active=True).count()
    return render_template('user/profile.html', solved=solved_challenges,
                           total_solved=len(solved_challenges),
                           category_stats=category_stats,
                           total_points=total_points,
                           total_active_challenges=total_active_challenges)


# ========== ADMIN DASHBOARD ==========
@app.route('/admin', endpoint='admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('challenges'))
    stats = {
        'total_users': User.query.count(),
        'total_challenges': Challenge.query.count(),
        'active_challenges': Challenge.query.filter_by(is_active=True).count(),
        'total_solves': SolvedChallenge.query.count()
    }
    recent_logs = FlagLog.query.order_by(FlagLog.submitted_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, recent_logs=recent_logs)


@app.route('/admin/challenges', endpoint='admin_challenges')
@login_required
def admin_challenges():
    if not current_user.is_admin: return redirect(url_for('challenges'))
    return render_template('admin/challenges.html', challenges=Challenge.query.all())


@app.route('/admin/challenges/add', methods=['GET', 'POST'])
@login_required
def add_challenge():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('challenges'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        points = int(request.form.get('points', 0))
        flag = request.form.get('flag')
        is_active = request.form.get('is_active') == 'on'

        # Конвертация хинтов из textarea в JSON
        hints_text = request.form.get('hints', '')
        hints_list = [h.strip() for h in hints_text.splitlines() if h.strip()]
        hints_json = json.dumps(hints_list)

        ch = Challenge(title=title, description=description, category=category,
                       points=points, flag=flag, hints=hints_json, is_active=is_active)
        db.session.add(ch)
        db.session.flush()  # Получаем ch.id до коммита

        # Сохранение файлов задания
        files = request.files.getlist('files')
        for f in files:
            if f and allowed_file(f.filename):
                fname = secure_filename(f"ch{ch.id}_{f.filename}")
                f.save(os.path.join('uploads/challenges', fname))

        # Райтап (файл)
        w_file = request.files.get('writeup_file')
        if w_file and allowed_file(w_file.filename):
            w_fname = secure_filename(f"wup_{ch.id}_{w_file.filename}")
            w_file.save(os.path.join('uploads/writeups', w_fname))
            ch.writeup_filename = w_fname

        # Ачивка
        ach_name = request.form.get('ach_name')
        ach_desc = request.form.get('ach_desc')
        if ach_name and ach_desc:
            ach_icon = 'default.png'
            icon_file = request.files.get('ach_icon')
            if icon_file and allowed_achievement_icon(icon_file.filename):
                ach_icon = secure_filename(f"ach_{ch.id}_{icon_file.filename}")
                icon_file.save(os.path.join('uploads/achievements', ach_icon))

            db.session.add(Achievement(name=ach_name, description=ach_desc, icon=ach_icon, challenge_id=ch.id))

        db.session.commit()
        flash('Задание успешно создано!', 'success')
        return redirect(url_for('admin_challenges'))

    return render_template('admin/add_challenge.html', categories=Config.CATEGORIES)


@app.route('/admin/challenges/edit/<int:challenge_id>', methods=['GET', 'POST'])
@login_required
def edit_challenge(challenge_id):
    if not current_user.is_admin: return redirect(url_for('challenges'))
    ch = Challenge.query.get_or_404(challenge_id)
    if request.method == 'POST':
        ch.title = request.form.get('title')
        ch.description = request.form.get('description')
        ch.category = request.form.get('category')
        ch.points = int(request.form.get('points', ch.points))
        ch.flag = request.form.get('flag')
        ch.hints = request.form.get('hints', ch.hints)
        ch.is_active = request.form.get('is_active') == 'on'

        # Райтап
        w_file = request.files.get('writeup_file')
        if w_file and allowed_file(w_file.filename):
            fname = secure_filename(f"{ch.id}_{w_file.filename}")
            w_file.save(os.path.join('uploads/writeups', fname))
            ch.writeup_filename = fname

        # Ачивка
        ach_name = request.form.get('ach_name')
        ach_desc = request.form.get('ach_desc')
        ach = Achievement.query.filter_by(challenge_id=ch.id).first()
        if ach_name and ach_desc:
            if ach:
                ach.name = ach_name
                ach.description = ach_desc
            else:
                db.session.add(Achievement(name=ach_name, description=ach_desc, icon='default.png', challenge_id=ch.id))
        elif ach:
            db.session.delete(ach)

        db.session.commit()
        flash('Задание обновлено!', 'success')
        return redirect(url_for('admin_challenges'))
    return render_template('admin/edit_challenge.html', challenge=ch, categories=Config.CATEGORIES)


@app.route('/admin/logs')
@login_required
def admin_logs():
    if not current_user.is_admin: return redirect(url_for('challenges'))
    page = request.args.get('page', 1, type=int)
    logs = FlagLog.query.order_by(FlagLog.submitted_at.desc()).paginate(page=page, per_page=50)
    return render_template('admin/logs.html', logs=logs)


@app.route('/admin/user/toggle_admin/<int:user_id>')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin: return redirect(url_for('challenges'))
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Права администратора {"выданы" if user.is_admin else "отозваны"} для {user.username}', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users', endpoint='admin_users')
@login_required
def admin_users():
    if not current_user.is_admin: return redirect(url_for('challenges'))
    return render_template('admin/users.html', users=User.query.all())


@app.route('/admin/writeups', endpoint='admin_writeups')
@login_required
def admin_writeups():
    if not current_user.is_admin: return redirect(url_for('challenges'))
    challenges = Challenge.query.filter(Challenge.writeup_filename != None).all()
    return render_template('admin/writeups.html', challenges=challenges)


@app.route('/admin/stats', endpoint='admin_stats')
@login_required
def admin_stats():
    if not current_user.is_admin: return redirect(url_for('challenges'))
    challenge_stats = []
    total_users = User.query.count()
    for challenge in Challenge.query.all():
        solves = SolvedChallenge.query.filter_by(challenge_id=challenge.id).count()
        pct = (solves / total_users) * 100 if total_users > 0 else 0
        challenge_stats.append({'challenge': challenge, 'solves': solves, 'solved_percentage': pct})

    category_stats = []
    for category in Config.CATEGORIES:
        cat_challenges = Challenge.query.filter_by(category=category, is_active=True).count()
        cat_solves = db.session.query(SolvedChallenge).join(Challenge).filter(
            Challenge.category == category, Challenge.is_active == True
        ).count()
        category_stats.append({'category': category, 'challenges': cat_challenges, 'solves': cat_solves})

    return render_template('admin/stats.html', challenge_stats=challenge_stats, category_stats=category_stats,
                           total_users=total_users)


# ================= CONTEXT PROCESSORS =================
@app.context_processor
def inject_global_vars():
    return dict(
        total_active_challenges=Challenge.query.filter_by(is_active=True).count(),
        categories=Config.CATEGORIES,
        total_users=User.query.count(),
        total_solves=SolvedChallenge.query.count()
    )


# ================= INITIAL SETUP =================
def create_tables():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('admin123'), is_admin=True)
            db.session.add(admin)
            db.session.commit()
            print('Admin user created: username=admin, password=admin123')


if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=False)