# server.py - version avec Supabase (PostgreSQL)
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import json
import os

import psycopg2
import psycopg2.extras

DATA = Path("data.json")          # on s'en sert encore une fois pour l'initialisation
SECRET_FILE = Path("admin_secret.txt")

# ---------- Connexion base Supabase ----------

DATABASE_URL = os.getenv("DATABASE_URL")  # doit être défini dans Render

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL n'est pas défini dans les variables d'environnement")

def get_conn():
    # Render/Supabase : SSL obligatoire
    return psycopg2.connect(DATABASE_URL, sslmode="require")


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


# ---------- Fonctions utilitaires DB ----------

def load_from_db():
    """
    Récupère toutes les cartes depuis Supabase et les renvoie
    dans le même format que data.json :
    {
      "categories": [{id, categorie, question, reponse}, ...],
      "bris": [{id, affirmation, reponse}, ...]
    }
    """
    data = {"categories": [], "bris": []}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # catégories
            cur.execute("""
                SELECT identifiant, categorie, question, reponse
                FROM categories
                ORDER BY identifiant
            """)
            for row in cur.fetchall():
                data["categories"].append({
                    "id": row["identifiant"],
                    "categorie": row["categorie"],
                    "question": row["question"],
                    "reponse": row["reponse"],
                })

            # bris d'égalité
            cur.execute("""
                SELECT identifiant, affirmation, reponse
                FROM bris
                ORDER BY identifiant
            """)
            for row in cur.fetchall():
                data["bris"].append({
                    "id": row["identifiant"],
                    "affirmation": row["affirmation"],
                    "reponse": row["reponse"],
                })

    return data


def save_to_db(payload: dict):
    """
    Remplace le contenu des tables par les données envoyées par l'admin.
    On supprime tout puis on réinsère (plus simple / 700 lignes seulement).
    """
    categories = payload.get("categories", []) or []
    bris = payload.get("bris", []) or []

    with get_conn() as conn:
        with conn.cursor() as cur:
            # on vide les tables
            cur.execute("DELETE FROM categories;")
            cur.execute("DELETE FROM bris;")

            # on remet les catégories
            for c in categories:
                cur.execute(
                    """
                    INSERT INTO categories(identifiant, categorie, question, reponse)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        int(c.get("id")),
                        c.get("categorie") or "",
                        c.get("question") or "",
                        c.get("reponse") or "",
                    ),
                )

            # on remet les bris d'égalité
            for b in bris:
                cur.execute(
                    """
                    INSERT INTO bris(identifiant, affirmation, reponse)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        int(b.get("id")),
                        b.get("affirmation") or "",
                        b.get("reponse") or "",
                    ),
                )

        conn.commit()


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

    # 1. si data.json existe et que les tables sont vides, on peut initialiser
    #    une seule fois depuis le fichier (premier déploiement).
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM categories;")
                nb_cat = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM bris;")
                nb_bris = cur.fetchone()[0]
    except Exception:
        nb_cat = nb_bris = 0

    if (nb_cat == 0 and nb_bris == 0) and DATA.exists():
        try:
            raw = json.loads(DATA.read_text(encoding="utf-8"))
            save_to_db(raw)
        except Exception:
            # en cas de souci, on ignore et on continue
            pass

    # 2. on renvoie toujours ce qui est dans la base Supabase
    data = load_from_db()
    return jsonify(data)


@APP.put("/api/data")
def put_data():
    if not check_auth(request):
        return ("", 401)

    payload = request.get_json(force=True)

    # sauvegarde dans Supabase
    save_to_db(payload)

    # on peut aussi garder une copie locale dans data.json (facultatif)
    try:
        DATA.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass

    return jsonify({"ok": True})


@APP.post("/api/change-password")
def change_password():
    """
    Change le mot de passe administrateur.

    - Authentification avec l'ancien mdp dans X-Admin-Key
    - Corps JSON : { "new_password": "..." }
    """
    if not check_auth(request):
        return ("", 401)

    data = request.get_json(force=True) or {}
    new_pwd = (data.get("new_password") or "").strip()

    if not new_pwd:
        return jsonify({"error": "missing new_password"}), 400

    save_secret(new_pwd)
    return jsonify({"ok": True})


# ---------- Routes pour les pages ----------

@APP.route("/")
def serve_index():
    # page principale (cartes pour les joueurs)
    return send_from_directory(".", "index.html")


@APP.route("/admin")
def serve_admin():
    # interface d'administration
    return send_from_directory(".", "admin.html")


# ---------- Lancement ----------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    APP.run(host="0.0.0.0", port=port, debug=True)
