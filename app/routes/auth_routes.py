from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from app.models.radiology_models import User
from app.services.audit_service import log_action


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


# =========================================================
# 🛡️ ROLE DECORATOR
# =========================================================
def role_required(*allowed_roles):
    """
    Protège les routes selon le rôle connecté.
    Empêche l'accès direct par URL si la session n'existe pas.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = session.get("role")
            username = session.get("username")

            # 🔐 Pas connecté
            if not role or not username:
                flash("Veuillez vous connecter 🔐", "warning")
                return redirect(url_for("auth.login"))

            # ⛔ Mauvais rôle
            if role not in allowed_roles:
                log_action(
                    username,
                    "Tentative accès refusé",
                    target=str(request.path),
                )

                flash("Accès refusé ⛔", "danger")
                return redirect(url_for("auth.login"))

            return view(*args, **kwargs)

        return wrapped

    return decorator


# =========================================================
# 🔐 LOGIN
# =========================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # 🚫 Si déjà connecté, renvoyer au dashboard
    if session.get("role") and session.get("username"):
        role_redirects = {
            "admin": "radiology.admin_dashboard",
            "major": "radiology.major_dashboard",
            "validator": "radiology.validator_dashboard",
            "secretary": "radiology.secretary_dashboard",
        }

        target_route = role_redirects.get(
            session.get("role"),
            "radiology.index"
        )
        return redirect(url_for(target_route))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # 🧹 Nettoyage ancienne session
            session.clear()

            # 🔐 Nouvelle session propre
            session["role"] = user.role
            session["username"] = user.username
            session["user_id"] = user.id
            session.permanent = True

            log_action(username, "Connexion")

            flash("Connexion réussie ✅", "success")

            # 🎯 Redirection intelligente selon le rôle
            role_redirects = {
                "admin": "radiology.admin_dashboard",
                "major": "radiology.major_dashboard",
                "validator": "radiology.validator_dashboard",
                "secretary": "radiology.secretary_dashboard",
            }

            target_route = role_redirects.get(
                user.role,
                "radiology.index"
            )

            return redirect(url_for(target_route))

        flash("Identifiants invalides ❌", "danger")

    return render_template("auth/login.html")


# =========================================================
# 🚪 LOGOUT
# =========================================================
@auth_bp.route("/logout")
def logout():
    username = session.get("username")

    if username:
        log_action(username, "Déconnexion")

    # 🧹 destruction totale session
    session.clear()

    flash("Déconnexion réussie 👋", "info")
    return redirect(url_for("auth.login"))