from app import create_app, db
from app.models.radiology_models import User

app = create_app()

with app.app_context():
    # 🔥 CRÉE LES TABLES SI ELLES N'EXISTENT PAS
    db.create_all()

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