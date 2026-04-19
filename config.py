import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 🔐 sécurité
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "radiology-coud-secret-key"
    )

    # 🗄️ base de données
    INSTANCE_FOLDER = os.path.join(BASE_DIR, "instance")
    DB_PATH = os.path.join(INSTANCE_FOLDER, "radiology_coud.db")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 🌍 URL de base pour QR (LOCAL + PROD)
    # 👉 priorité à la variable d’environnement (important)
    BASE_URL = os.environ.get(
        "BASE_URL",
        "http://192.168.1.2:5000"
    )

    # 📂 uploads sécurisés
    UPLOAD_FOLDER = os.path.join(INSTANCE_FOLDER, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    # 📎 formats autorisés
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    # 📁 création automatique des dossiers
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)