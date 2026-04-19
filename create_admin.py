from app import db
from app.models.radiology_models import User


def create_users():
    users = [
        ("admin", "admin"),
        ("major", "major"),
        ("validator", "validator"),
        ("secretary", "secretary"),
    ]

    for username, role in users:
        existing = User.query.filter_by(username=username).first()

        if not existing:
            user = User(username=username, role=role)
            user.set_password("1234")
            db.session.add(user)
            print(f"{username} créé ✅")
        else:
            print(f"{username} existe déjà ✅")

    db.session.commit()
    print("Tous les comptes sont prêts 🔐")