import os
from flask import Flask, session  # Добавьте session здесь
from .config import Config
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=None):
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    cfg = config_class or Config()
    app.config.from_object(cfg)

    db.init_app(app)
    migrate.init_app(app, db)

    # services
    from .services.media_service import MediaService
    app.media_service = MediaService(app)

    # optionally start media watcher if enabled
    if app.config.get("WATCH_MEDIA", False):
        try:
            started = app.media_service.start_watcher()
            if started:
                app.logger.info("Media watcher started")
        except Exception as e:
            app.logger.warning(f"Failed to start media watcher: {e}")

    # blueprints
    from .routes import main_bp
    from .api import api_bp
    from .auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.context_processor
    def inject_user_id():
        """Добавить user_id в контекст всех шаблонов"""
        user_id = session.get("user_id")
        return {"USER_ID": user_id}

    # Создать админа по умолчанию при первом запуске
    with app.app_context():
        try:
            from .models import User
            
            # Проверяем, существует ли таблица users
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                admin = User.query.filter_by(username="admin").first()
                if not admin:
                    admin = User(
                        username="admin",
                        email="admin@localhost",
                        avatar="👑",
                        is_admin=True
                    )
                    db.session.add(admin)
                    db.session.commit()
                    app.logger.info("Default admin user created")
                else:
                    # Убедимся, что существующий пользователь admin имеет права администратора
                    if not admin.is_admin:
                        admin.is_admin = True
                        admin.avatar = "👑"
                        db.session.commit()
                        app.logger.info("Updated existing admin user with admin privileges")
        except Exception as e:
            app.logger.error(f"Error creating default admin: {e}")
            # Не прерываем запуск, возможно таблицы ещё не созданы

    return app