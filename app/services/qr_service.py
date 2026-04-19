import os
import qrcode
from flask import current_app


def generate_qr_code(token):
    """
    Génère un QR code intelligent :
    - QR patient → accès direct RDV
    - QR public → accès formulaire général
    - compatible mobile + production
    """

    # 📁 dossier QR
    folder = os.path.join(current_app.root_path, "static", "qr_codes")
    os.makedirs(folder, exist_ok=True)

    # 📄 nom fichier sécurisé
    filename = f"{token}.png"
    filepath = os.path.join(folder, filename)

    # 🌍 base URL (config ou fallback)
    base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000")
    base_url = base_url.rstrip("/")  # 🔥 évite double slash

    # 🔥 LOGIQUE INTELLIGENTE QR
    if token == "public_rdv":
        qr_data = f"{base_url}/radiology/new"
    else:
        qr_data = f"{base_url}/radiology/rdv/{token}"

    # 🧠 génération QR (pro)
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)

    # 🔁 chemin relatif pour HTML/PDF
    return os.path.join("static", "qr_codes", filename)