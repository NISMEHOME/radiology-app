from datetime import datetime
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from app import db


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
# 👤 PATIENT
# =========================================================
class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)

    patient_number = db.Column(
        db.String(30),
        unique=True,
        nullable=False,
    )

    patient_type = db.Column(
        db.String(20),
        nullable=False,
    )  # student, staff, external

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    matricule = db.Column(db.String(50), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    # 🔗 Relations
    requests = db.relationship(
        "RadiologyRequest",
        backref="patient",
        lazy=True,
        cascade="all, delete-orphan",
    )

    appointments = db.relationship(
        "Appointment",
        backref="patient",
        lazy=True,
        cascade="all, delete-orphan",
    )

    emergency_requests = db.relationship(
        "EmergencyRequest",
        backref="patient",
        lazy=True,
        cascade="all, delete-orphan",
    )

    recommendations = db.relationship(
        "RecommendationRequest",
        backref="patient",
        lazy=True,
        cascade="all, delete-orphan",
    )

    folders = db.relationship(
        "PatientFolder",
        backref="patient",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return (
            f"<Patient {self.patient_number} - "
            f"{self.first_name} {self.last_name}>"
        )


# =========================================================
# 📄 DEMANDE RADIOLOGIE + RÉSULTATS PDF
# =========================================================
class RadiologyRequest(db.Model):
    __tablename__ = "radiology_requests"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False,
    )

    # 📎 fichiers
    bulletin_file = db.Column(
        db.String(255),
        nullable=False,
    )

    support_file_1 = db.Column(
        db.String(255),
        nullable=True,
    )

    support_file_2 = db.Column(
        db.String(255),
        nullable=True,
    )

    # 🩻 informations examen
    exam_type = db.Column(
        db.String(100),
        nullable=False,
        default="Radiographie Thorax",
    )

    body_part = db.Column(
        db.String(100),
        nullable=True,
    )

    indication = db.Column(
        db.Text,
        nullable=True,
    )

    machine_used = db.Column(
        db.String(100),
        nullable=True,
    )

    radiologist_name = db.Column(
        db.String(100),
        nullable=True,
    )

    # 📄 compte rendu
    result_text = db.Column(
        db.Text,
        nullable=True,
    )

    conclusion = db.Column(
        db.Text,
        nullable=True,
    )

    pdf_result_file = db.Column(
        db.String(255),
        nullable=True,
    )

    result_qr_code = db.Column(
        db.String(255),
        nullable=True,
    )

    result_generated_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    result_status = db.Column(
        db.String(30),
        default="pending_result",
    )

    status = db.Column(
        db.String(30),
        default="pending_review",
    )

    validator_comment = db.Column(
        db.Text,
        nullable=True,
    )

    is_duplicate = db.Column(
        db.Boolean,
        default=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    appointments = db.relationship(
        "Appointment",
        backref="radiology_request",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def result_pdf(self):
        return self.pdf_result_file

    @result_pdf.setter
    def result_pdf(self, value):
        self.pdf_result_file = value

    @property
    def result_qr(self):
        return self.result_qr_code

    @result_qr.setter
    def result_qr(self, value):
        self.result_qr_code = value

    @property
    def completed_at(self):
        return self.result_generated_at

    @completed_at.setter
    def completed_at(self, value):
        self.result_generated_at = value

    def __repr__(self):
        return (
            f"<RadiologyRequest {self.id} - "
            f"{self.exam_type} - "
            f"{self.result_status}>"
        )


# =========================================================
# 🗓️ RENDEZ-VOUS
# =========================================================
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False,
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("radiology_requests.id"),
        nullable=False,
    )

    appointment_datetime = db.Column(
        db.DateTime,
        nullable=False,
    )

    qr_token = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
    )

    is_checked_in = db.Column(
        db.Boolean,
        default=False,
    )

    is_completed = db.Column(
        db.Boolean,
        default=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"<Appointment {self.id} - "
            f"{self.appointment_datetime}>"
        )


# =========================================================
# 📁 DOSSIER PATIENT UNIQUE
# =========================================================
class PatientFolder(db.Model):
    __tablename__ = "patient_folders"

    id = db.Column(db.Integer, primary_key=True)

    folder_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id"),
        nullable=True,
    )

    status = db.Column(
        db.String(50),
        default="pending_review",
        nullable=False,
        index=True,
    )

    assigned_secretary = db.Column(
        db.String(120),
        nullable=True,
    )

    assigned_major = db.Column(
        db.String(120),
        nullable=True,
    )

    # ✅ NOUVEAU : remise finale au patient
    delivered_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    delivered_by = db.Column(
        db.String(120),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    appointment = db.relationship(
        "Appointment",
        backref=db.backref("folder", uselist=False),
    )

    exams = db.relationship(
        "RequestedExam",
        backref="folder",
        lazy=True,
        cascade="all, delete-orphan",
    )

    workflow_logs = db.relationship(
        "WorkflowLog",
        backref="folder",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<PatientFolder {self.folder_number} - "
            f"{self.status}>"
        )

# =========================================================
# 🩻 EXAMENS MULTIPLES PAR DOSSIER
# =========================================================
class RequestedExam(db.Model):
    __tablename__ = "requested_exams"

    id = db.Column(db.Integer, primary_key=True)

    folder_id = db.Column(
        db.Integer,
        db.ForeignKey("patient_folders.id"),
        nullable=False,
        index=True,
    )

    exam_type = db.Column(db.String(150), nullable=False)
    body_part = db.Column(db.String(150), nullable=True)
    indication = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(30), default="normal")

    status = db.Column(
        db.String(50),
        default="pending_major",
        nullable=False,
        index=True,
    )

    result_text = db.Column(db.Text, nullable=True)
    result_pdf = db.Column(db.String(255), nullable=True)

    # 🔥 CORRECTION CRITIQUE (manquait)
    result_qr = db.Column(db.String(255), nullable=True)

    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<RequestedExam {self.exam_type} - {self.status}>"
    

# =========================================================
# 📝 JOURNAL DE WORKFLOW / AUDIT DOSSIER
# =========================================================
class WorkflowLog(db.Model):
    __tablename__ = "workflow_logs"

    id = db.Column(db.Integer, primary_key=True)

    folder_id = db.Column(
        db.Integer,
        db.ForeignKey("patient_folders.id"),
        nullable=False,
        index=True,
    )

    action = db.Column(db.String(150), nullable=False)
    actor_role = db.Column(db.String(50), nullable=False)
    actor_name = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )


# =========================================================
# 🚨 URGENCES
# =========================================================
class EmergencyRequest(db.Model):
    __tablename__ = "emergency_requests"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False,
    )

    emergency_bulletin = db.Column(
        db.String(255),
        nullable=False,
    )

    major_confirmed = db.Column(
        db.Boolean,
        default=False,
    )

    confirmed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"<EmergencyRequest {self.id} - "
            f"confirmed={self.major_confirmed}>"
        )


# =========================================================
# 🩺 RECOMMANDATIONS MÉDICALES → MAJOR ONLY
# =========================================================
class RecommendationRequest(db.Model):
    __tablename__ = "recommendation_requests"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False,
    )

    recommendation_file = db.Column(
        db.String(255),
        nullable=False,
    )

    note = db.Column(
        db.Text,
        nullable=True,
    )

    major_seen = db.Column(
        db.Boolean,
        default=False,
    )

    seen_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"<RecommendationRequest {self.id} - "
            f"seen={self.major_seen}>"
        )


# =========================================================
# 🔐 UTILISATEURS SYSTÈME
# =========================================================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.String(30),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password,
        )

    def __repr__(self):
        return f"<User {self.username} - {self.role}>"


# =========================================================
# 📝 AUDIT LOGS GLOBAUX
# =========================================================
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        nullable=False,
    )

    action = db.Column(
        db.String(255),
        nullable=False,
    )

    target = db.Column(
        db.String(255),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"<AuditLog {self.username} - "
            f"{self.action}>"
        )


# =========================================================
# 🛠️ HELPERS
# =========================================================
def generate_folder_number(last_id=None):
    """
    Génère un numéro dossier unique.
    Exemple: COUD-RAD-2026-000001
    """
    year = datetime.utcnow().year
    next_number = (last_id or 0) + 1
    return f"COUD-RAD-{year}-{next_number:06d}"