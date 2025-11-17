# server.py
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import json, os

DATA = Path("data.json")
SECRET_FILE = Path("admin_secret.txt")

# ---------- Gestion du mot de passe admin ----------

def load_secret():
    """Charge le mot de passe admin depuis un fichier ou la variable d'env."""
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    env = os.getenv("ADMIN_SECRET")
    if env:
        return env.strip()
    # mot de passe par défaut si rien n'existe encore
    return "change-me-please"

def save_secret(new_secret: str):
    """Enregistre le mot de passe admin dans le fichier et en mémoire."""
    global ADMIN_SECRET
    new_secret = new_secret.strip()
    SECRET_FILE.write_text(new_secret, encoding="utf-8")
    ADMIN_SECRET = new_secret

ADMIN_SECRET = load_secret()

APP = Flask(__name__, static_url_path="", static_folder=".")

def check_auth(req) -> bool:
    """Vérifie que le header X-Admin-Key correspond au mot de passe courant."""
    return req.headers.get("X-Admin-Key", "") == ADMIN_SECRET

# ---------- Endpoints API ----------

@APP.get("/api/ping")
def ping():
    if not check_auth(request):
        return ("", 401)
    return ("", 204)

@APP.get("/api/data")
def get_data():
    if not check_auth(request):
        return ("", 401)
    # renvoie data.json tel quel
    return send_from_directory(".", "data.json")

@APP.put("/api/data")
def put_data():
    if not check_auth(request):
        return ("", 401)
    payload = request.get_json(force=True)
    DATA.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return jsonify({"ok": True})

@APP.post("/api/change-password")
def change_password():
    """
    Change le mot de passe administrateur.

    - Authentification avec l'ancien mdp dans X-Admin-Key
    - Corps JSON : { "new_password": "..." }
    """
    # Vérifie d'abord l'ancien mot de passe
    if not check_auth(request):
        return ("", 401)

    data = request.get_json(force=True) or {}
    new_pwd = (data.get("new_password") or "").strip()

    if not new_pwd:
        return jsonify({"error": "missing new_password"}), 400

    save_secret(new_pwd)
    return jsonify({"ok": True})

# ---------- Lancement ----------
@APP.route("/")
def serve_index():
    # page principale (cartes pour les joueurs)
    return send_from_directory(".", "index.html")

@APP.route("/admin")
def serve_admin():
    # interface d'administration
    return send_from_directory(".", "admin.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    APP.run(host="0.0.0.0", port=port, debug=True)

