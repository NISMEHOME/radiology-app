from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ⏳ Session expire après 30 min
    app.permanent_session_lifetime = timedelta(minutes=30)

    # 🗄️ Initialisation extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # 📦 Import modèles (IMPORTANT pour migrations)
    from app.models import (
        Patient,
        RadiologyRequest,
        Appointment,
        EmergencyRequest,
    )

    # 📡 IMPORT + ENREGISTREMENT BLUEPRINTS
    from app.routes.radiology_routes import radiology_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(radiology_bp)
    app.register_blueprint(auth_bp)

    # 🔥 INITIALISATION DB + USERS (APRÈS IMPORTS → IMPORTANT)
    with app.app_context():
        db.create_all()

        try:
            from create_admin import create_users

            # ⚠️ protection anti boucle
            if not getattr(app, "_users_initialized", False):
                create_users()
                app._users_initialized = True
                print("✅ Utilisateurs initialisés")

        except Exception as e:
            print("⚠️ Erreur création utilisateurs :", e)

    # 🚫 Désactiver cache navigateur
    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, "
            "post-check=0, pre-check=0, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app