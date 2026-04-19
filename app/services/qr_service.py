import os
import qrcode
import hashlib
from flask import current_app


def generate_qr_code(data):
    """
    Génère un QR code à partir d'une URL ou donnée brute.

    ✔️ Cache intelligent (1 URL = 1 QR)
    ✔️ Compatible local + production
    ✔️ Aucun lien codé en dur
    ✔️ Optimisé performance
    """

    # 📁 dossier QR
    folder = os.path.join(current_app.root_path, "static", "qr_codes")
    os.makedirs(folder, exist_ok=True)

    # 🔒 nom fichier basé sur hash UNIQUE de l'URL
    filename = hashlib.md5(data.encode()).hexdigest() + ".png"
    filepath = os.path.join(folder, filename)

    # 🔥 ÉVITER DE RECRÉER SI EXISTE
    if os.path.exists(filepath):
        return os.path.join("static", "qr_codes", filename)

    # 🧠 génération QR
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)

    # 🔁 chemin relatif pour HTML/PDF
    return os.path.join("static", "qr_codes", filename)