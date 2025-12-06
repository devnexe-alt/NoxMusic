from functools import wraps
from flask import Blueprint, request, current_app, jsonify, session, render_template, redirect, url_for, flash
from .models import User
from . import db

auth_bp = Blueprint("auth", __name__)

def require_api_key(func):
    """Декоратор для проверки API ключа (для старых эндпоинтов)"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not key or key != current_app.config["ADMIN_API_KEY"]:
            return jsonify({"error": "invalid_api_key"}), 401
        return func(*args, **kwargs)
    return wrapper

def require_admin(func):
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # API-ключ в header/query имеет приоритет
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key and key == current_app.config["ADMIN_API_KEY"]:
            return func(*args, **kwargs)
        
        # Проверка сессии пользователя
        user_id = session.get("user_id")
        if user_id:
            user = User.query.get(user_id)
            if user and user.is_admin:
                return func(*args, **kwargs)
        
        # Если ajax/JSON — вернуть 401, иначе редирект на логин
        if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
            return jsonify({"error": "admin_required"}), 403
        
        flash("Admin access required", "error")
        return redirect(url_for("auth.login", next=request.path))
    return wrapper

def require_login(func):
    """Декоратор для проверки авторизации пользователя"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
                return jsonify({"error": "login_required"}), 401
            flash("Please log in to continue", "error")
            return redirect(url_for("auth.login", next=request.path))
        return func(*args, **kwargs)
    return wrapper


def require_auth(roles=None):
    """
    Универсальный декоратор для проверки авторизации с ролями
    roles: список разрешённых ролей, например ['admin', 'user'] или только ['admin']
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Проверка API ключа (для админов)
            key = request.headers.get("X-API-Key") or request.args.get("api_key")
            if key and key == current_app.config["ADMIN_API_KEY"]:
                # Если есть API ключ админа, пропускаем
                return func(*args, **kwargs)
            
            # Проверка сессии
            user_id = session.get("user_id")
            if not user_id:
                if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
                    return jsonify({"error": "authentication_required"}), 401
                flash("Please log in to continue", "error")
                return redirect(url_for("auth.login", next=request.path))
            
            user = User.query.get(user_id)
            if not user:
                session.clear()
                return redirect(url_for("auth.login"))
            
            # Проверка ролей, если указаны
            if roles:
                user_role = 'admin' if user.is_admin else 'user'
                if user_role not in roles:
                    if request.is_json:
                        return jsonify({"error": "insufficient_permissions"}), 403
                    flash("Insufficient permissions", "error")
                    return redirect(url_for("main.index"))
            
            # Добавляем пользователя в контекст
            request.user = user
            return func(*args, **kwargs)
        return wrapper
    return decorator

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Страница входа"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        api_key = request.form.get("api_key", "").strip()
        next_url = request.args.get("next") or url_for("main.index")
        
        # Вход через API ключ (для админа)
        if api_key and api_key == current_app.config["ADMIN_API_KEY"]:
            # Найти или создать админа
            admin = User.query.filter_by(username="admin").first()
            if not admin:
                admin = User(username="admin", is_admin=True, avatar="👨‍💼")
                db.session.add(admin)
                db.session.commit()
            
            session["user_id"] = admin.id
            session["is_admin"] = True
            flash("Logged in as admin", "success")
            return redirect(next_url)
        
        # Вход через username (простой вариант без пароля)
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                session["user_id"] = user.id
                session["is_admin"] = user.is_admin
                flash(f"Welcome back, {user.username}!", "success")
                return redirect(next_url)
            else:
                flash("User not found. Try registering first.", "error")
        else:
            flash("Please enter username or API key", "error")
    
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Регистрация нового пользователя"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        avatar = request.form.get("avatar", "👤").strip()
        
        if not username:
            flash("Username is required", "error")
            return redirect(url_for("auth.register"))
        
        # Проверка на существование
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Username already taken", "error")
            return redirect(url_for("auth.register"))
        
        if email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash("Email already registered", "error")
                return redirect(url_for("auth.register"))
        
        # Создать пользователя
        user = User(
            username=username,
            email=email or None,
            avatar=avatar,
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        
        # Автоматический вход после регистрации
        session["user_id"] = user.id
        session["is_admin"] = False
        
        flash(f"Welcome, {username}! Your account has been created.", "success")
        return redirect(url_for("main.index"))
    
    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    """Выход из системы"""
    username = None
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        if user:
            username = user.username
    
    session.clear()
    
    if username:
        flash(f"Goodbye, {username}!", "success")
    else:
        flash("Logged out", "success")
    
    return redirect(url_for("main.index"))

@auth_bp.route("/profile")
@require_login
def profile():
    """Профиль пользователя"""
    user_id = session.get("user_id")
    user = User.query.get_or_404(user_id)
    
    # Статистика
    from .models import ListeningHistory, LikedTrack, Playlist
    
    total_plays = ListeningHistory.query.filter_by(user_id=user.id).count()
    total_likes = LikedTrack.query.filter_by(user_id=user.id).count()
    total_playlists = Playlist.query.filter_by(user_id=user.id).count()
    
    # Недавние прослушивания
    recent = ListeningHistory.query.filter_by(user_id=user.id)\
        .order_by(ListeningHistory.played_at.desc())\
        .limit(10).all()
    
    return render_template(
        "profile.html",
        user=user,
        total_plays=total_plays,
        total_likes=total_likes,
        total_playlists=total_playlists,
        recent=recent
    )

@auth_bp.route("/profile/edit", methods=["GET", "POST"])
@require_login
def profile_edit():
    """Редактирование профиля"""
    user_id = session.get("user_id")
    user = User.query.get_or_404(user_id)
    
    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_email = request.form.get("email", "").strip()
        new_avatar = request.form.get("avatar", "").strip()
        
        # Проверка уникальности username
        if new_username != user.username:
            existing = User.query.filter_by(username=new_username).first()
            if existing:
                flash("Username already taken", "error")
                return redirect(url_for("auth.profile_edit"))
            user.username = new_username
        
        # Проверка уникальности email
        if new_email and new_email != user.email:
            existing = User.query.filter_by(email=new_email).first()
            if existing:
                flash("Email already registered", "error")
                return redirect(url_for("auth.profile_edit"))
            user.email = new_email
        
        if new_avatar:
            user.avatar = new_avatar
        
        db.session.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for("auth.profile"))
    
    return render_template("profile_edit.html", user=user)

@auth_bp.route("/ping")
def ping():
    """Health check"""
    return {"status": "ok"}

@auth_bp.route("/whoami")
def whoami():
    """Информация о текущем пользователе"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False})
    
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False})
    
    return jsonify({
        "authenticated": True,
        "user": user.to_dict()
    })

# Context processor для доступа к user в шаблонах
@auth_bp.app_context_processor
def inject_user():
    """Добавить текущего пользователя в контекст всех шаблонов"""
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        return {"current_user": user}
    return {"current_user": None}

# Добавить в auth.py после существующих декораторов
