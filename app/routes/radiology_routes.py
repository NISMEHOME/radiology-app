from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from sqlalchemy import func, or_
import os
import uuid
from app import db
from app.models.radiology_models import (
    Patient,
    RadiologyRequest,
    Appointment,
    EmergencyRequest,
    RecommendationRequest,
    PatientFolder,
    RequestedExam,
    WorkflowLog,
    generate_folder_number,
)
from app.services.appointment_service import (
    generate_patient_number,
    get_next_available_appointment,
)
from app.services.qr_service import generate_qr_code
from app.services.pdf_service import (
    generate_appointment_pdf,
    generate_radiology_result_pdf,
)
from app.routes.auth_routes import role_required


# =========================================================
# 📡 BLUEPRINT RADIOLOGIE
# =========================================================
radiology_bp = Blueprint(
    "radiology",
    __name__,
    url_prefix="/radiology",
)

# =========================================================
# 📥 DOWNLOAD PDF RDV
# =========================================================
@radiology_bp.route("/download-appointment/<path:filename>")
def download_appointment_pdf(filename):
    return send_from_directory(
        current_app.instance_path,
        filename,
        as_attachment=True
    )

# =========================================================
# 📥 DOWNLOAD FICHIERS (BULLETIN + SUPPORTS) ✅ FIX
# =========================================================
@radiology_bp.route("/file/<path:filename>")
def download_result_file(filename):
    try:
        # 🔥 normalisation du chemin (ULTRA IMPORTANT)
        if filename.startswith("uploads/"):
            filename = filename[len("uploads/"):]

        file_path = os.path.join(
            current_app.instance_path,
            "uploads",
            filename
        )

        # 🔍 DEBUG (tu peux supprimer après)
        print("FILE PATH:", file_path)

        # ❌ fichier inexistant
        if not os.path.exists(file_path):
            print("FICHIER INTROUVABLE:", file_path)
            flash("Fichier introuvable ❌", "danger")
            return redirect(url_for("radiology.validator_dashboard"))

        # ✅ ouvrir fichier
        return send_from_directory(
            os.path.join(current_app.instance_path, "uploads"),
            filename,
            as_attachment=False
        )

    except Exception as e:
        print("ERREUR FICHIER:", filename, e)
        flash("Erreur lors de l'ouverture du fichier ❌", "danger")
        return redirect(url_for("radiology.validator_dashboard"))

# =========================================================
# 🩻 TYPES RADIOLOGIE
# =========================================================
RADIOLOGY_TYPES = [
    "Radiographie Thorax",
    "Radiographie Crâne",
    "Radiographie Abdomen",
    "Radiographie Bassin",
    "Radiographie Colonne",
    "Radiographie Membre supérieur",
    "Radiographie Membre inférieur",
    "Échographie abdominale",
    "Échographie obstétricale",
    "Scanner cérébral",
    "Scanner thoracique",
    "Scanner abdominal",
    "IRM cérébrale",
    "IRM rachis",
    "Mammographie",
]


# =========================================================
# 👩‍💼 EXAMENS DISPONIBLES AU SECRÉTARIAT
# =========================================================
SECRETARY_EXAMS = [
    "Radiographie Thorax",
    "Radiographie Crâne",
    "Radiographie Abdomen",
    "Radiographie Bassin",
    "Scanner cérébral",
    "Scanner thoracique",
    "Scanner abdominal",
    "Échographie abdominale",
    "Échographie obstétricale",
    "IRM cérébrale",
    "IRM rachis",
    "Mammographie",
]


def save_file(file, folder):
    if not file or file.filename == "":
        return None

    allowed_extensions = current_app.config.get(
        "ALLOWED_EXTENSIONS", {"pdf", "png", "jpg", "jpeg"}
    )

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in allowed_extensions:
        raise ValueError("Format de fichier non autorisé")

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

    upload_path = os.path.join(
        current_app.instance_path,
        "uploads",
        folder,
    )
    os.makedirs(upload_path, exist_ok=True)

    filepath = os.path.join(upload_path, filename)
    file.save(filepath)

    return os.path.join("uploads", folder, filename)


@radiology_bp.route("/")
def index():
    role = session.get("role")

    role_redirects = {
        "admin": "radiology.admin_dashboard",
        "major": "radiology.major_dashboard",
        "validator": "radiology.validator_dashboard",
        "secretary": "radiology.secretary_dashboard",
    }

    return redirect(url_for(role_redirects.get(role, "auth.login")))


@radiology_bp.route("/qr-entry")
def qr_entry():
    return redirect(url_for("radiology.new_request"))


@radiology_bp.route("/scan/<qr_type>")
def smart_qr_router(qr_type):
    routes = {
        "normal": "radiology.new_request",
        "emergency": "radiology.emergency_request",
        "recommendation": "radiology.recommendation_request",
    }

    target = routes.get(qr_type)

    if not target:
        flash("QR code invalide ❌", "danger")
        return redirect(url_for("radiology.index"))

    return redirect(url_for(target))


@radiology_bp.route("/new", methods=["GET", "POST"])
def new_request():
    if request.method == "POST":
        try:
            # 🧪 DEBUG (tu peux supprimer après test)
            print("FORM DATA:", request.form)
            print("FILES:", request.files)

            # ✅ récupération sécurisée
            patient_type = request.form.get("patient_type")
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            phone = request.form.get("phone")
            matricule = request.form.get("matricule")

            birth_date_str = request.form.get("birth_date")

            if not all([patient_type, first_name, last_name, phone, birth_date_str]):
                raise ValueError("Champs obligatoires manquants")

            try:
                birth_date = datetime.strptime(
                    birth_date_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValueError("Format de date invalide")

            # ❗ IMPORTANT → ton HTML n'a PAS exam_type
            exam_type = request.form.get("exam_type") or "Radiographie Thorax"

            # =========================
            # 👤 PATIENT
            # =========================
            patient = Patient(
                patient_number=generate_patient_number(),
                patient_type=patient_type,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                phone=phone,
                matricule=matricule,
            )
            db.session.add(patient)
            db.session.flush()

            # =========================
            # 📄 DEMANDE RADIO
            # =========================
            radio_request = RadiologyRequest(
                patient_id=patient.id,
                exam_type=exam_type,
                body_part=request.form.get("body_part"),
                indication=request.form.get("indication"),
                bulletin_file=save_file(
                    request.files.get("bulletin_file"), "bulletins"
                ),
                support_file_1=save_file(
                    request.files.get("support_file_1"), "supports"
                ),
                support_file_2=save_file(
                    request.files.get("support_file_2"), "supports"
                ),
                status="pending_review",
            )
            db.session.add(radio_request)
            db.session.flush()

            # =========================
            # 📅 RDV AUTO
            # =========================
            appointment = Appointment(
                patient_id=patient.id,
                request_id=radio_request.id,
                appointment_datetime=get_next_available_appointment(),
                qr_token=uuid.uuid4().hex,
            )
            db.session.add(appointment)
            db.session.flush()


            # =========================
            # 📁 DOSSIER UNIQUE
            # =========================
            last_folder = PatientFolder.query.order_by(
                PatientFolder.id.desc()
            ).first()

            folder_number = generate_folder_number(
                last_folder.id if last_folder else 0
            )

            patient_folder = PatientFolder(
                folder_number=folder_number,
                patient_id=patient.id,
                appointment_id=appointment.id,
                status="pending_review",
            )
            db.session.add(patient_folder)
            db.session.flush()

            # =========================
            # 📝 LOG WORKFLOW
            # =========================
            db.session.add(
                WorkflowLog(
                    folder_id=patient_folder.id,
                    action="Dossier créé automatiquement après scan QR",
                    actor_role="patient",
                    actor_name=f"{patient.first_name} {patient.last_name}",
                    notes="Création complète automatique",
                )
            )

            db.session.commit()

            flash(f"Rendez-vous créé ✅ Dossier: {folder_number}", "success")

            return redirect(
                url_for("radiology.success", appointment_id=appointment.id)
            )

        except Exception as e:
            db.session.rollback()
            print("ERREUR:", str(e))  # debug console
            flash(f"Erreur : {str(e)}", "danger")
            return redirect(url_for("radiology.new_request"))

    return render_template(
        "radiology/new_request.html",
        radiology_types=RADIOLOGY_TYPES,
    )
@radiology_bp.route("/success/<int:appointment_id>")
def success(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    # 🔥 Génération QR (UTILISE CONFIG BASE_URL automatiquement)
    qr_path = generate_qr_code(appointment.qr_token)

    # 📄 PDF
    pdf_path = generate_appointment_pdf(appointment, qr_path)

    return render_template(
        "radiology/success.html",
        appointment=appointment,
        pdf_path=pdf_path,
        qr_path=qr_path,
    )

@radiology_bp.route("/secretary/folder/<int:folder_id>", methods=["GET", "POST"])
@role_required("secretary", "admin")
def secretary_folder_detail(folder_id):
    folder = PatientFolder.query.get_or_404(folder_id)

    if request.method == "POST":
        try:
            selected_exams = request.form.getlist("selected_exams")
            indication = request.form.get("indication")
            priority = request.form.get("priority", "normal")

            if not selected_exams:
                flash("Veuillez sélectionner au moins un examen", "warning")
                return redirect(
                    url_for("radiology.secretary_folder_detail", folder_id=folder.id)
                )

            created_exams = []
            for exam_type in selected_exams:
                existing = RequestedExam.query.filter_by(
                    folder_id=folder.id,
                    exam_type=exam_type,
                ).first()

                if existing:
                    continue

                db.session.add(
                    RequestedExam(
                        folder_id=folder.id,
                        exam_type=exam_type,
                        indication=indication,
                        priority=priority,
                        status="pending_major",
                    )
                )
                created_exams.append(exam_type)

            if not created_exams:
                flash("Tous les examens sélectionnés existent déjà", "warning")
                return redirect(
                    url_for("radiology.secretary_folder_detail", folder_id=folder.id)
                )
            folder.status = "sent_to_major"
            folder.assigned_secretary = session.get("username", "Secrétaire")

            db.session.add(
                WorkflowLog(
                    folder_id=folder.id,
                    action="Examens sélectionnés et dossier envoyé au major",
                    actor_role="secretary",
                    actor_name=session.get("username", "Secrétaire"),
                    notes=f"Examens: {', '.join(created_exams)}",
                )
            )

            db.session.commit()

            flash("Examens ajoutés et dossier envoyé au major ✅", "success")
            return redirect(url_for("radiology.secretary_dashboard"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur examens : {str(e)}", "danger")

    existing_exams = RequestedExam.query.filter_by(folder_id=folder.id).all()

    return render_template(
        "radiology/secretary_folder_detail.html",
        folder=folder,
        available_exams=SECRETARY_EXAMS,
        existing_exams=existing_exams,
    )


@radiology_bp.route("/validator")
@role_required("validator", "admin")
def validator_dashboard():
    requests = RadiologyRequest.query.filter_by(
        status="pending_review"
    ).order_by(
        RadiologyRequest.created_at.desc()
    ).all()

    return render_template(
        "radiology/validator_dashboard.html",
        requests=requests,
    )


@radiology_bp.route("/validator/update/<int:request_id>", methods=["POST"])
@role_required("validator", "admin")
def update_request_status(request_id):
    try:
        radio_request = RadiologyRequest.query.get_or_404(request_id)
        new_status = request.form["status"]
        comment = request.form.get("comment")

        radio_request.status = new_status
        radio_request.validator_comment = comment

        folder = (
            PatientFolder.query.filter_by(
                patient_id=radio_request.patient_id
            )
            .order_by(PatientFolder.id.desc())
            .first()
        )

        if folder and new_status == "conforme":
            folder.status = "validated"

            db.session.add(
                WorkflowLog(
                    folder_id=folder.id,
                    action="Dossier validé et envoyé au secrétariat",
                    actor_role="validator",
                    actor_name=session.get("username", "Valideur"),
                    notes=comment,
                )
            )

        db.session.commit()

        flash("Dossier validé et transféré au secrétariat ✅", "success")
        return redirect(url_for("radiology.validator_dashboard"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur validation : {str(e)}", "danger")
        return redirect(url_for("radiology.validator_dashboard"))


@radiology_bp.route("/major")
@role_required("major", "admin")
def major_dashboard():

    folders = PatientFolder.query.filter(
        PatientFolder.status == "sent_to_major"
    ).order_by(
        PatientFolder.created_at.desc()
    ).all()

    print("DEBUG MAJOR FOLDERS:", folders)  # 🔥 DEBUG

    emergencies = EmergencyRequest.query.order_by(
        EmergencyRequest.created_at.desc()
    ).all()

    recommendations = RecommendationRequest.query.order_by(
        RecommendationRequest.created_at.desc()
    ).all()

    requests_completed = RadiologyRequest.query.filter(
        RadiologyRequest.status == "completed"
    ).count()

    return render_template(
        "radiology/major_dashboard.html",
        folders=folders,
        emergencies=emergencies,
        recommendations=recommendations,
        requests_completed=requests_completed,
    )

# =========================================================
# 👨🏽‍⚕️ ÉTAPE 4 — MAJOR → MULTI RÉSULTATS → PDF → SECRÉTAIRE
# =========================================================
@radiology_bp.route("/major/folder/<int:folder_id>", methods=["GET", "POST"])
@role_required("major", "admin")
def major_folder_detail(folder_id):
    folder = PatientFolder.query.get_or_404(folder_id)
    exams = RequestedExam.query.filter_by(folder_id=folder.id).all()

    if request.method == "POST":
        try:
            completed_exams = []

            for exam in exams:
                result_text = request.form.get(f"result_text_{exam.id}")

                if result_text:
                    exam.result_text = result_text
                    exam.status = "completed"
                    exam.completed_at = datetime.utcnow()

                    qr_token = uuid.uuid4().hex
                    qr_path = generate_qr_code(qr_token)

                    class _RadioRequestAdapter:
                        pass

                    adapter = _RadioRequestAdapter()
                    adapter.id = exam.id
                    adapter.patient = folder.patient
                    adapter.exam_type = exam.exam_type
                    adapter.indication = exam.indication
                    adapter.result_text = exam.result_text
                    adapter.completed_at = exam.completed_at
                    adapter.result_qr = qr_token

                    pdf_path = generate_radiology_result_pdf(adapter, qr_path)
                    exam.result_pdf = pdf_path
                    exam.result_qr = qr_token
                    completed_exams.append(exam.exam_type)
            if not completed_exams:
                flash("Veuillez saisir au moins un résultat", "warning")
                return redirect(
                    url_for("radiology.major_folder_detail", folder_id=folder.id)
                )
            folder.status = "ready_for_delivery"
            folder.assigned_major = session.get("username", "Major")

            db.session.add(
                WorkflowLog(
                    folder_id=folder.id,
                    action="Résultats saisis et dossier retourné au secrétariat",
                    actor_role="major",
                    actor_name=session.get("username", "Major"),
                    notes=f"Examens finalisés: {', '.join(completed_exams)}",
                )
            )

            db.session.commit()

            flash(
                "Résultats enregistrés et dossier prêt pour remise ✅",
                "success",
            )
            return redirect(url_for("radiology.major_dashboard"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur saisie résultats : {str(e)}", "danger")

    return render_template(
        "radiology/major_folder_detail.html",
        folder=folder,
        exams=exams,
    )


@radiology_bp.route("/major/recommendation/<int:recommendation_id>", methods=["POST"])
@role_required("major", "admin")
def mark_recommendation_seen(recommendation_id):
    recommendation = RecommendationRequest.query.get_or_404(recommendation_id)
    recommendation.major_seen = True
    recommendation.seen_at = datetime.utcnow()
    db.session.commit()

    flash("Recommandation consultée ✅", "success")
    return redirect(url_for("radiology.major_dashboard"))


@radiology_bp.route("/major/confirm/<int:emergency_id>", methods=["POST"])
@role_required("major", "admin")
def confirm_emergency(emergency_id):
    emergency = EmergencyRequest.query.get_or_404(emergency_id)
    emergency.major_confirmed = True
    emergency.confirmed_at = datetime.utcnow()
    db.session.commit()

    flash("Urgence confirmée par le Major ✅", "success")
    return redirect(url_for("radiology.major_dashboard"))


@radiology_bp.route("/secretary")
@role_required("secretary", "admin")
def secretary_dashboard():
    # ✅ dossiers validés venant du valideur
    folders_pending = (
        PatientFolder.query.filter_by(status="validated")
        .order_by(PatientFolder.created_at.desc())
        .all()
    )

    # ✅ dossiers prêts après résultats major
    folders_ready = (
        PatientFolder.query.filter_by(status="ready_for_delivery")
        .order_by(PatientFolder.updated_at.desc())
        .all()
    )

    return render_template(
        "radiology/secretary_dashboard.html",
        folders_pending=folders_pending,
        folders_ready=folders_ready,
    )


@radiology_bp.route("/secretary/results")
@role_required("secretary", "admin")
def secretary_ready_results():
    ready_folders = (
        PatientFolder.query.filter_by(status="ready_for_delivery")
        .order_by(PatientFolder.updated_at.desc())
        .all()
    )

    return render_template(
        "radiology/secretary_ready_results.html",
        folders=ready_folders,
    )

# =========================================================
# 📦 REMISE FINALE + ARCHIVAGE DOSSIER
# =========================================================
@radiology_bp.route("/secretary/delivery/<int:folder_id>", methods=["GET", "POST"])
@role_required("secretary", "admin")
def secretary_delivery(folder_id):
    folder = PatientFolder.query.get_or_404(folder_id)

    exams = RequestedExam.query.filter_by(
        folder_id=folder.id
    ).order_by(
        RequestedExam.requested_at.asc()
    ).all()

    if request.method == "POST":
        try:
            # ✅ sécuriser : tous les examens doivent être finalisés
            incomplete_exams = [
                exam for exam in exams if exam.status != "completed"
            ]

            if incomplete_exams:
                flash(
                    "Impossible de remettre : certains examens ne sont pas finalisés ❌",
                    "danger",
                )
                return redirect(
                    url_for("radiology.secretary_delivery", folder_id=folder.id)
                )

            folder.status = "archived"
            folder.delivered_at = datetime.utcnow()
            folder.delivered_by = session.get("username", "Secrétaire")

            db.session.add(
                WorkflowLog(
                    folder_id=folder.id,
                    action="Résultats remis au patient et dossier archivé",
                    actor_role="secretary",
                    actor_name=session.get("username", "Secrétaire"),
                    notes=f"{len(exams)} PDF remis au patient",
                )
            )

            db.session.commit()

            flash("Résultats remis et dossier archivé ✅", "success")
            return redirect(url_for("radiology.secretary_dashboard"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur archivage : {str(e)}", "danger")

    return render_template(
        "radiology/secretary_delivery.html",
        folder=folder,
        exams=exams,
    )

# =========================================================
# 🧾 SAISIE RÉSULTAT RADIO + PDF
# =========================================================
@radiology_bp.route("/result/<int:request_id>", methods=["GET", "POST"])
@role_required("major", "admin")
def radiology_result(request_id):
    radio_request = RadiologyRequest.query.get_or_404(request_id)

    if request.method == "POST":
        try:
            radio_request.result_text = request.form["result_text"]
            radio_request.status = "completed"
            radio_request.completed_at = datetime.utcnow()

            qr_token = uuid.uuid4().hex
            qr_path = generate_qr_code(qr_token)

            pdf_path = generate_radiology_result_pdf(
                radio_request,
                qr_path,
            )

            radio_request.result_pdf = pdf_path
            radio_request.result_qr = qr_token

            db.session.commit()

            flash("Compte rendu généré avec succès ✅", "success")
            return redirect(
                url_for("radiology.view_result", request_id=request_id)
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur résultat : {str(e)}", "danger")

    return render_template(
        "radiology/result_form.html",
        radio_request=radio_request,
    )


# =========================================================
# 👁️ AFFICHER RÉSULTAT
# =========================================================
@radiology_bp.route("/result/view/<int:request_id>")
def view_result(request_id):
    radio_request = RadiologyRequest.query.get_or_404(request_id)
    return render_template(
        "radiology/result_view.html",
        radio_request=radio_request,
    )


# =========================================================
# 📥 DOWNLOAD PDF RÉSULTAT
# =========================================================
@radiology_bp.route("/result/download/<int:request_id>")
def download_result_pdf(request_id):
    radio_request = RadiologyRequest.query.get_or_404(request_id)

    if not radio_request.result_pdf:
        flash("PDF non disponible", "warning")
        return redirect(url_for("radiology.view_result", request_id=request_id))

    return send_from_directory(
        current_app.instance_path,
        radio_request.result_pdf.replace("uploads/", ""),
        as_attachment=True,
    )


# =========================================================
# 📱 VERIFY RESULT QR
# =========================================================
@radiology_bp.route("/verify-result/<token>")
def verify_result(token):
    exam = RequestedExam.query.filter_by(result_qr=token).first()

    if exam:
        return render_template(
            "radiology/result_verify.html",
            exam=exam,
        )

    radio_request = RadiologyRequest.query.filter_by(
        result_qr=token
    ).first_or_404()

    return render_template(
        "radiology/result_verify.html",
        radio_request=radio_request,
    )
# =========================================================
# 📱 RDV DIRECT VIA QR (NOUVEAU 🔥)
# =========================================================
@radiology_bp.route("/rdv/<token>")
def rdv_from_qr(token):
    appointment = Appointment.query.filter_by(qr_token=token).first()

    if not appointment:
        flash("QR invalide ❌", "danger")
        return redirect(url_for("radiology.index"))

    return render_template(
        "radiology/new_request.html",
        radiology_types=RADIOLOGY_TYPES,
        appointment=appointment  # 🔥 IMPORTANT
    )

# =========================================================
# 🚨 URGENCE
# =========================================================
@radiology_bp.route("/emergency/new", methods=["GET", "POST"])
@role_required("secretary", "major", "admin")
def emergency_request():
    if request.method == "POST":
        try:
            patient_id = request.form["patient_id"]

            emergency = EmergencyRequest(
                patient_id=patient_id,
                emergency_bulletin=save_file(
                    request.files.get("emergency_bulletin"),
                    "emergency",
                ),
            )
            db.session.add(emergency)
            db.session.flush()

            last_folder = PatientFolder.query.order_by(
                PatientFolder.id.desc()
            ).first()

            folder_number = generate_folder_number(
                last_folder.id if last_folder else 0
            )

            urgent_folder = PatientFolder(
                folder_number=folder_number,
                patient_id=patient_id,
                status="urgent_direct_major",
            )
            db.session.add(urgent_folder)
            db.session.flush()

            db.session.add(
                WorkflowLog(
                    folder_id=urgent_folder.id,
                    action="Urgence envoyée directement au major",
                    actor_role="doctor",
                    actor_name=session.get("username", "Médecin"),
                    notes="Bypass valideur + secrétaire",
                )
            )

            db.session.commit()

            flash("Urgence envoyée directement au Major 🚨", "warning")
            return redirect(url_for("radiology.emergency_success"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur urgence : {str(e)}", "danger")

    return render_template("radiology/emergency_request.html")


# =========================================================
# ✅ SUCCESS URGENCE
# =========================================================
@radiology_bp.route("/emergency/success")
@role_required("secretary", "major", "admin")
def emergency_success():
    return render_template("radiology/emergency_success.html")


# =========================================================
# 🩺 RECOMMANDATION
# =========================================================
@radiology_bp.route("/recommendation/new", methods=["GET", "POST"])
def recommendation_request():
    if request.method == "POST":
        try:
            patient_id = request.form["patient_id"]

            recommendation = RecommendationRequest(
                patient_id=patient_id,
                recommendation_file=save_file(
                    request.files.get("recommendation_file"),
                    "recommendations",
                ),
                note=request.form.get("note"),
            )
            db.session.add(recommendation)
            db.session.flush()

            last_folder = PatientFolder.query.order_by(
                PatientFolder.id.desc()
            ).first()

            folder_number = generate_folder_number(
                last_folder.id if last_folder else 0
            )

            recommendation_folder = PatientFolder(
                folder_number=folder_number,
                patient_id=patient_id,
                status="recommendation_direct_major",
            )
            db.session.add(recommendation_folder)
            db.session.flush()

            db.session.add(
                WorkflowLog(
                    folder_id=recommendation_folder.id,
                    action="Recommandation envoyée directement au major",
                    actor_role="doctor",
                    actor_name=session.get("username", "Médecin"),
                    notes="Bypass workflow normal",
                )
            )

            db.session.commit()

            flash("Recommandation envoyée directement au Major 🩺", "success")
            return redirect(url_for("radiology.recommendation_success"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur recommandation : {str(e)}", "danger")

    return render_template("radiology/recommendation_request.html")


# =========================================================
# ✅ SUCCESS RECOMMANDATION
# =========================================================
@radiology_bp.route("/recommendation/success")
@role_required("secretary", "major", "admin")
def recommendation_success():
    return render_template("radiology/recommendation_success.html")

# =========================================================
# 🧑🏽‍💼 DASHBOARD ADMIN + ANALYTICS
# =========================================================
@radiology_bp.route("/admin")
@role_required("admin")
def admin_dashboard():
    today = date.today()

    total_patients = Patient.query.count()
    total_requests = RadiologyRequest.query.count()
    total_appointments = Appointment.query.count()
    total_emergencies = EmergencyRequest.query.count()

    # ✅ analytics examens réels du workflow
    total_requested_exams = RequestedExam.query.count()
    completed_requested_exams = RequestedExam.query.filter_by(
        status="completed"
    ).count()
    pending_requested_exams = RequestedExam.query.filter(
        RequestedExam.status != "completed"
    ).count()

    appointments_today = Appointment.query.filter(
        func.date(Appointment.appointment_datetime) == today
    ).count()

    completed_today = Appointment.query.filter(
        func.date(Appointment.appointment_datetime) == today,
        Appointment.is_completed.is_(True),
    ).count()

    checked_in_today = Appointment.query.filter(
        func.date(Appointment.appointment_datetime) == today,
        Appointment.is_checked_in.is_(True),
    ).count()

    attendance_rate = (
        round((checked_in_today / appointments_today) * 100, 1)
        if appointments_today else 0
    )

    machine_load = round((appointments_today / 25) * 100, 1)

    labels = []
    appointments_series = []
    completed_series = []
    emergencies_series = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime("%d/%m"))

        appointments_series.append(
            Appointment.query.filter(
                func.date(Appointment.appointment_datetime) == day
            ).count()
        )

        completed_series.append(
            Appointment.query.filter(
                func.date(Appointment.appointment_datetime) == day,
                Appointment.is_completed.is_(True),
            ).count()
        )

        emergencies_series.append(
            EmergencyRequest.query.filter(
                func.date(EmergencyRequest.created_at) == day
            ).count()
        )

    exam_stats = db.session.query(
        RadiologyRequest.exam_type,
        func.count(RadiologyRequest.id)
    ).group_by(RadiologyRequest.exam_type).all()

    return render_template(
        "radiology/admin_dashboard.html",
        total_patients=total_patients,
        total_requests=total_requests,
        total_appointments=total_appointments,
        total_emergencies=total_emergencies,
        appointments_today=appointments_today,
        completed_today=completed_today,
        attendance_rate=attendance_rate,
        machine_load=machine_load,
        labels=labels,
        appointments_series=appointments_series,
        completed_series=completed_series,
        emergencies_series=emergencies_series,
        exam_stats=exam_stats,
        total_requested_exams=total_requested_exams,
        completed_requested_exams=completed_requested_exams,
        pending_requested_exams=pending_requested_exams,
    )


# =========================================================
# 📝 JOURNAL D'AUDIT
# =========================================================
@radiology_bp.route("/audit")
@role_required("admin")
def audit_dashboard():
    recent_requests = RadiologyRequest.query.order_by(
        RadiologyRequest.created_at.desc()
    ).limit(20).all()

    recent_emergencies = EmergencyRequest.query.order_by(
        EmergencyRequest.created_at.desc()
    ).limit(20).all()

    recent_recommendations = RecommendationRequest.query.order_by(
        RecommendationRequest.created_at.desc()
    ).limit(20).all()

    completed_results = RadiologyRequest.query.filter(
        RadiologyRequest.status == "completed"
    ).order_by(
        RadiologyRequest.created_at.desc()
    ).limit(20).all()

    total_completed = RadiologyRequest.query.filter(
        RadiologyRequest.status == "completed"
    ).count()

    total_pending = RadiologyRequest.query.filter(
        RadiologyRequest.status == "pending_review"
    ).count()

    total_conforme = RadiologyRequest.query.filter(
        RadiologyRequest.status == "conforme"
    ).count()

    total_urgent = EmergencyRequest.query.count()

    return render_template(
        "radiology/audit_dashboard.html",
        recent_requests=recent_requests,
        recent_emergencies=recent_emergencies,
        recent_recommendations=recent_recommendations,
        completed_results=completed_results,
        total_completed=total_completed,
        total_pending=total_pending,
        total_conforme=total_conforme,
        total_urgent=total_urgent,
    )

# =========================================================
# 🗃️ DASHBOARD ARCHIVES + RECHERCHE
# =========================================================
@radiology_bp.route("/archives")
@role_required("secretary", "admin")
def archives_dashboard():
    query = PatientFolder.query.filter_by(status="archived")

    folder_number = request.args.get("folder_number", "").strip()
    patient_name = request.args.get("patient_name", "").strip()
    archive_date = request.args.get("archive_date", "").strip()

    if folder_number:
        query = query.filter(
            PatientFolder.folder_number.ilike(f"%{folder_number}%")
        )

    if patient_name:
        query = query.join(Patient).filter(
            or_(
                Patient.first_name.ilike(f"%{patient_name}%"),
                Patient.last_name.ilike(f"%{patient_name}%"),
            )
        )

    if archive_date:
        try:
            selected_date = datetime.strptime(
                archive_date,
                "%Y-%m-%d"
            ).date()

            query = query.filter(
                func.date(PatientFolder.delivered_at) == selected_date
            )
        except ValueError:
            flash("Date invalide", "warning")

    folders = query.order_by(
        PatientFolder.delivered_at.desc()
    ).all()

    return render_template(
        "radiology/archives_dashboard.html",
        folders=folders,
        folder_number=folder_number,
        patient_name=patient_name,
        archive_date=archive_date,
    )

# =========================================================
# 📱 VERIFY RDV
# =========================================================
@radiology_bp.route("/verify/<token>")
@role_required("secretary", "validator", "major", "admin")
def verify_qr(token):
    appointment = Appointment.query.filter_by(qr_token=token).first_or_404()

    return render_template(
        "radiology/verify.html",
        appointment=appointment,
    )


# =========================================================
# ✅ CHECK-IN
# =========================================================
@radiology_bp.route("/check-in/<int:appointment_id>", methods=["POST"])
@role_required("secretary", "admin")
def check_in_patient(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.is_checked_in = True
    db.session.commit()

    flash("Patient marqué comme arrivé ✅", "success")
    return redirect(url_for("radiology.secretary_dashboard"))


# =========================================================
# 🏁 EXAMEN TERMINÉ
# =========================================================
@radiology_bp.route("/complete/<int:appointment_id>", methods=["POST"])
@role_required("secretary", "admin")
def complete_exam(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.is_completed = True
    db.session.commit()

    flash("Examen marqué terminé ✅", "success")
    return redirect(url_for("radiology.secretary_dashboard"))
# =========================================================
# 🖨️ QR PUBLIC À IMPRIMER (CORRECT)
# =========================================================
@radiology_bp.route("/qr-print")
def qr_print():
    base_url = current_app.config.get("BASE_URL", "http://192.168.1.2:5000")
    base_url = base_url.rstrip("/")

    url = f"{base_url}/radiology/new"

    qr_path = generate_qr_code("public_rdv")

    return render_template(
        "radiology/qr_print.html",
        qr_path=qr_path,
        url=url
    )