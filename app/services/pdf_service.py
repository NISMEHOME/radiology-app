import os
from flask import render_template, current_app
from weasyprint import HTML

# =========================================================
# 📄 PDF RDV PATIENT (VERSION DESIGN PRO AVEC LOGO)
# =========================================================
def generate_appointment_pdf(appointment, qr_path):
    folder = os.path.join(
        current_app.instance_path,
        "uploads",
        "appointments"
    )
    os.makedirs(folder, exist_ok=True)

    filename = f"appointment_{appointment.id}.pdf"
    filepath = os.path.join(folder, filename)

    # 🔥 génération HTML (design pro)
    html_content = render_template(
        "radiology/pdf/appointment.html",
        appointment=appointment,
        qr_path=qr_path
    )

    # 🔥 conversion PDF
    HTML(
        string=html_content,
        base_url=current_app.root_path
    ).write_pdf(filepath)

    # ✅ chemin relatif pour téléchargement Flask
    return os.path.join("uploads", "appointments", filename)

# =========================================================
# 🧠 MAPPING TEMPLATE HTML
# =========================================================
def get_pdf_template(exam_type):
    mapping = {
        "Scanner cérébral": "radiology/pdf/scanner_brain.html",
        "Radiographie Thorax": "radiology/pdf/thorax.html",
        "Radiographie Abdomen": "radiology/pdf/abdomen.html",

        "Échographie abdominale": "radiology/pdf/echographie_abdominale.html",
        "Échographie pelvienne": "radiology/pdf/echographie_pelvienne.html",
        "Échographie mammaire": "radiology/pdf/echographie_mammaire.html",
        "Échographie obstétricale 1er trimestre": "radiology/pdf/echo_obstetricale_trim1.html",
        "Échographie obstétricale": "radiology/pdf/echo_obstetricale_trim23.html",
        "Échographie obstétricale 2eme trimestre": "radiology/pdf/echo_obstetricale_trim23.html",
        "Échographie obstétricale 3eme trimestre": "radiology/pdf/echo_obstetricale_trim23.html",
        "Échographie arbre urinaire": "radiology/pdf/arbre_urinaire.html",
        "Échographie cervicale": "radiology/pdf/cervicale.html",
        "Échographie des bourses": "radiology/pdf/bourses.html",
        "Échographie des parties molles": "radiology/pdf/parties_molles.html",
        "Échographie abdomino-pelvienne": "radiology/pdf/echographie_abdomino_pelvienne.html",
    }

    return mapping.get(
        exam_type,
        "radiology/pdf/default.html"
    )


# =========================================================
# 🩻 TEXTE PAR DÉFAUT
# =========================================================
def get_default_result_template(exam_type):
    templates = {
        "Radiographie Thorax": (
            "Poumons bien expansés.\n"
            "Pas d'opacité focale.\n"
            "Silhouette cardiaque normale.\n"
            "Conclusion : RAS."
        ),
        "Scanner cérébral": (
            "Ventricules normaux.\n"
            "Pas d'hémorragie.\n"
            "Ligne médiane respectée.\n"
            "Conclusion : scanner normal."
        ),
        "Échographie abdominale": (
            "Foie homogène.\n"
            "Reins normaux.\n"
            "Pas d'épanchement."
        ),
    }

    return templates.get(
        exam_type,
        "Compte rendu radiologique sans anomalie majeure."
    )


# =========================================================
# 📄 PDF RÉSULTAT RADIO (HTML → PDF)
# =========================================================
def generate_radiology_result_pdf(radio_request, qr_path):
    folder = os.path.join(
        current_app.instance_path,
        "uploads",
        "results"
    )
    os.makedirs(folder, exist_ok=True)

    filename = f"result_{radio_request.id}.pdf"
    filepath = os.path.join(folder, filename)

    # ✅ correction QR
    qr_filename = os.path.basename(qr_path) if qr_path else None
    qr_url = f"/static/qrcodes/{qr_filename}" if qr_filename else None

    if not radio_request.result_text:
        radio_request.result_text = get_default_result_template(
            radio_request.exam_type
        )

    template_path = get_pdf_template(radio_request.exam_type)

    html_content = render_template(
        template_path,
        radio_request=radio_request,
        qr_path=qr_url
    )

    HTML(
        string=html_content,
        base_url=current_app.root_path
    ).write_pdf(filepath)

    return os.path.join("uploads", "results", filename)