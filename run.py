from flask import redirect, url_for
from app import create_app

app = create_app()

# ✅ ROUTE PRINCIPALE (évite le Not Found sur /)
@app.route("/")
def home():
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    # 🔥 IMPORTANT pour accès mobile (QR)
    app.run(host="0.0.0.0", port=5000, debug=True)