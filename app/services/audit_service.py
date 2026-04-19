from app import db
from app.models.radiology_models import AuditLog


def log_action(username, action, target=None):
    """
    Journalise toutes les actions critiques.
    """
    log = AuditLog(
        username=username,
        action=action,
        target=target,
    )
    db.session.add(log)
    db.session.commit()