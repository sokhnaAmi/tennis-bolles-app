# server.py
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import json, os

import psycopg2
from psycopg2.extras import RealDictCursor

DATA = Path("data.json")
SECRET_FILE = Path("admin_secret.txt")

# ---------- Configuration base de données ----------

DATABASE_URL = os.getenv("DATABASE_URL")
USE_DB = bool(DATABASE_URL)  # True sur Render (avec Supabase), False en local

def get_conn():
    """Ouvre une connexion PostgreSQL si DATABASE_URL est défini."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini")
    return psycopg2.connect(DATABASE_URL)

def load_all_data():
    """
    Charge toutes les cartes.
    - Si USE_DB = True : depuis la base (Supabase)
    - Sinon : depuis data.json (mode local)
    """
    if not USE_DB:
        # lecture depuis le fichier JSON (comportement actuel)
        if not DATA.exists():
            return {"categories": [], "bris": []}
        return json.loads(DATA.read_text(encoding="utf-8"))

    # --- Lecture depuis la base Postgres ---
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, categorie, question, reponse "
                "FROM categories ORDER BY id;"
            )
            categories = [dict(row) for row in cur.fetchall()]

            cur.execute(
                "SELECT id, affirmation, reponse "
                "FROM bris ORDER BY id;"
            )
            bris = [dict(row) for row in cur.fetchall()]

    return {"categories": categories, "bris": bris}


def save_all_data(payload: dict):
    """
    Enregistre toutes les cartes.
    - Si USE_DB = True : écrase le contenu des tables dans la base
    - Sinon : réécrit data.json
    """
    if not USE_DB:
        # écriture dans le fichier JSON (comportement actuel)
        DATA.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    cats = payload.get("categories", []) or []
    bris = payload.get("bris", []) or []

    with get_conn() as conn:
        with conn.cursor() as cur:
            # On vide les tables et on réinsère tout
            cur.execute("TRUNCATE TABLE categories RESTART IDENTITY;")
            cur.execute("TRUNCATE TABLE bris RESTART IDENTITY;")

            # Catégories
            for c in cats:
                cur.execute(
                    """
                    INSERT INTO categories (id, categorie, question, reponse)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        c.get("id"),
                        c.get("categorie"),
                        c.get("question"),
                        c.get("reponse"),
                    ),
                )

            # Bris d’égalité
            for b in bris:
                cur.execute(
                    """
                    INSERT INTO bris (id, affirmation, reponse)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        b.get("id"),
                        b.get("affirmation"),
                        b.get("reponse"),
                    ),
                )

        conn.commit()


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
    data = load_all_data()
    return jsonify(data)


@APP.put("/api/data")
def put_data():
    if not check_auth(request):
        return ("", 401)
    payload = request.get_json(force=True)
    save_all_data(payload)
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


# ---------- Lancement / routes HTML ----------

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
