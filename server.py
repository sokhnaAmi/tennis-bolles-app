# server.py — version avec Supabase (PostgreSQL)

from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import json, os

import psycopg2
import psycopg2.extras

DATA = Path("data.json")          # on s'en sert encore une fois pour le bootstrap + backup
SECRET_FILE = Path("admin_secret.txt")

DATA = Path("data.json")
SECRET_FILE = Path("admin_secret.txt")

# ---------- Connexion base Neon (PostgreSQL) ----------

DATABASE_URL = os.getenv("DATABASE_URL")  # définie dans Render

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL n'est pas défini dans les variables d'environnement")

def get_conn():
    # Neon / Render : SSL obligatoire
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def bootstrap_from_json_if_needed():
    """
    - Crée les tables 'categories' et 'bris' si elles n'existent pas.
    - Si elles sont vides, importe toutes les cartes depuis data.json.
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) Créer les tables si besoin
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id        INTEGER PRIMARY KEY,
            categorie TEXT    NOT NULL,
            question  TEXT    NOT NULL,
            reponse   TEXT    NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bris (
            id         INTEGER PRIMARY KEY,
            affirmation TEXT   NOT NULL,
            reponse     TEXT   NOT NULL
        );
    """)
    conn.commit()

    # 2) Vérifier si elles sont déjà remplies
    cur.execute("SELECT COUNT(*) FROM categories;")
    nb_cat = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bris;")
    nb_bris = cur.fetchone()[0]

    if nb_cat > 0 or nb_bris > 0:
        # On a déjà importé les données, on ne refait rien
        conn.close()
        return

    # 3) Charger data.json
    with DATA.open(encoding="utf-8") as f:
        raw = json.load(f)

    # data.json a la forme :
    # { "categories": [...], "bris": [...] }

    cats = [
        (c["id"], c["categorie"], c["question"], c["reponse"])
        for c in raw.get("categories", [])
    ]
    bris = [
        (b["id"], b["affirmation"], b["reponse"])
        for b in raw.get("bris", [])
    ]

    # 4) Insert en bulk
    if cats:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO categories (id, categorie, question, reponse) VALUES %s",
            cats,
        )

    if bris:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO bris (id, affirmation, reponse) VALUES %s",
            bris,
        )

    conn.commit()
    conn.close()


# On lance le bootstrap au démarrage du serveur
bootstrap_from_json_if_needed()



# ---------- Gestion du mot de passe admin (stocké dans Neon) ----------

def ensure_admin_secret():
    """
    S'assure qu'il existe une table admin_settings et une ligne (id=1)
    avec un mot de passe. Utilise ADMIN_SECRET (env) ou "change-me-please"
    comme valeur par défaut la première fois.
    """
    default_pwd = os.getenv("ADMIN_SECRET", "change-me-please").strip()

    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            # Table pour le mot de passe admin
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_settings (
                    id integer PRIMARY KEY,
                    admin_secret text NOT NULL
                );
                """
            )
            # Si aucune ligne, on insère le mot de passe par défaut
            cur.execute("SELECT admin_secret FROM admin_settings WHERE id = 1;")
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO admin_settings (id, admin_secret) VALUES (1, %s);",
                    (default_pwd,),
                )


def load_secret():
    """
    Charge le mot de passe admin depuis la base Neon.
    En cas de gros problème de BD, on retombe sur fichier/env.
    """
    try:
        ensure_admin_secret()
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT admin_secret FROM admin_settings WHERE id = 1;"
                )
                row = cur.fetchone()
                if row and row[0]:
                    return row[0].strip()
    except Exception as e:
        print("ERREUR load_secret (DB):", e, flush=True)

    # Fallback si vraiment la BD est KO
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    env = os.getenv("ADMIN_SECRET")
    if env:
        return env.strip()
    return "change-me-please"


def save_secret(new_secret: str):
    """
    Sauvegarde le mot de passe dans Neon (et met à jour la variable globale).
    """
    global ADMIN_SECRET
    new_secret = new_secret.strip()

    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO admin_settings (id, admin_secret)
                    VALUES (1, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET admin_secret = EXCLUDED.admin_secret;
                    """,
                    (new_secret,),
                )
    except Exception as e:
        print("ERREUR save_secret (DB):", e, flush=True)

    # Copie locale facultative (si jamais un jour tu veux regarder le fichier)
    try:
        SECRET_FILE.write_text(new_secret, encoding="utf-8")
    except Exception:
        pass

    ADMIN_SECRET = new_secret


# Mot de passe actuellement en vigueur en mémoire
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
    """
    Renvoie toutes les cartes depuis Supabase
    sous forme de JSON : { "categories": [...], "bris": [...] }
    compatible avec l'interface admin existante.
    """
    if not check_auth(request):
        return ("", 401)

    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Catégories
        cur.execute('SELECT "id", "categorie", "question", "reponse" '
                    'FROM "categories" ORDER BY "id";')
        rows_cat = cur.fetchall()
        categories = []
        for r in rows_cat:
            categories.append({
                "id": r["id"],
                "categorie": r["categorie"],
                "question": r["question"],
                "reponse": r["reponse"],
            })

        # Bris d'égalité
        cur.execute('SELECT "id", "affirmation", "reponse" '
                    'FROM bris ORDER BY "id";')
        rows_bris = cur.fetchall()
        bris_list = []
        for r in rows_bris:
            bris_list.append({
                "id": r["id"],
                "affirmation": r["affirmation"],
                "reponse": r["reponse"],
            })

        payload = {"categories": categories, "bris": bris_list}

        # on garde aussi une copie locale dans data.json (backup)
        DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return jsonify(payload)
    finally:
        conn.close()

@APP.get("/public-data")
def public_data():
    """
    Endpoint public pour l’interface joueurs.
    Lit directement dans la base Neon (sans mot de passe admin).
    """
    try:
        conn = get_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # --- Catégories ---
                cur.execute(
                    'SELECT "id", "categorie", "question", "reponse" '
                    'FROM categories ORDER BY "id";'
                )
                rows_cat = cur.fetchall()
                categories = [
                    {
                        "id": r["id"],
                        "categorie": r["categorie"],
                        "question": r["question"],
                        "reponse": r["reponse"],
                    }
                    for r in rows_cat
                ]

                # --- Bris d’égalité ---
                cur.execute(
                    'SELECT "id", "affirmation", "reponse" '
                    'FROM bris ORDER BY "id";'
                )
                rows_bris = cur.fetchall()
                bris_list = [
                    {
                        "id": r["id"],
                        "affirmation": r["affirmation"],
                        "reponse": r["reponse"],
                    }
                    for r in rows_bris
                ]

        return jsonify({"categories": categories, "bris": bris_list})

    except Exception as e:
        print("ERREUR /public-data:", e, flush=True)
        return jsonify({"erreur": "erreur de base de données"}), 500


@APP.put("/api/data")
def put_data():
    """
    Remplace toutes les cartes dans Supabase
    en fonction du JSON envoyé par l'interface admin.
    """
    if not check_auth(request):
        return ("", 401)

    payload = request.get_json(force=True) or {}
    cats = payload.get("categories", [])
    bris_list = payload.get("bris", [])

    conn = get_conn()
    try:
        cur = conn.cursor()

        # On efface tout, puis on ré-insère
        cur.execute('DELETE FROM "categories";')
        cur.execute('DELETE FROM bris;')

        for c in cats:
            cur.execute(
                'INSERT INTO "categories" ("id", "categorie", "question", "reponse") '
                'VALUES (%s, %s, %s, %s);',
                (
                    c.get("id"),
                    c.get("categorie"),
                    c.get("question"),
                    c.get("reponse"),
                ),
            )

        for b in bris_list:
            cur.execute(
                'INSERT INTO bris ("id", "affirmation", "reponse") '
                'VALUES (%s, %s, %s);',
                (
                    b.get("id"),
                    b.get("affirmation"),
                    b.get("reponse"),
                ),
            )

        conn.commit()

        # copie locale (backup)
        DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return jsonify({"ok": True})
    finally:
        conn.close()


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


# ---------- Routes front ----------

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
