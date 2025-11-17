# fuse_word_to_excel.py
# pip install python-docx pandas openpyxl
from docx import Document
import pandas as pd
from pathlib import Path

CATEGORIES_FILES = [
    ("Qui.docx",       0,   "Qui"),
    ("Quoi.docx",      100, "Quoi"),
    ("Ou.docx",        200, "Où"),   # mets "Où.docx" si c'est le vrai nom
    ("Quand.docx",     300, "Quand"),
    ("Comment.docx",   400, "Comment"),
    ("Combien.docx",   500, "Combien"),
    ("As.docx",        600, "As"),
]

BRIS_FILE = "Bris.docx"   # facultatif
OUTPUT_XLSX = "jeu_bolles.xlsx"

def paragraphs_to_blocks(doc):
    """Découpe le document en blocs séparés par AU MOINS une ligne vide."""
    blocks, cur = [], []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            cur.append(t)
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    return blocks

def split_question_answer(block):
    """
    block = liste de lignes non vides.
    La question peut tenir sur plusieurs lignes; elle se termine
    dès qu'on rencontre une ligne qui finit par '?'.
    Le reste du bloc = réponse (peut être multi-lignes).
    """
    q_lines, r_lines = [], []
    in_question = True
    for line in block:
        if in_question:
            q_lines.append(line)
            if line.rstrip().endswith("?"):
                in_question = False
        else:
            r_lines.append(line)
    question = " ".join(q_lines).strip()
    reponse = " ".join(r_lines).strip()
    return question, reponse

def extract_items_from_docx(path):
    """
    Ne dépend PAS de la numérotation Word.
    Suppose : un item = bloc (question multi-lignes finissant par '?', puis réponse)
    et les items sont séparés par des paragraphes vides.
    """
    doc = Document(path)
    blocks = paragraphs_to_blocks(doc)
    items = []
    for idx, block in enumerate(blocks, start=1):
        q, r = split_question_answer(block)
        items.append({"local_id": idx, "question": q, "reponse": r})
    return items

def build_categories_dataframe():
    all_rows = []
    for filepath, offset, categorie in CATEGORIES_FILES:
        p = Path(filepath)
        if not p.exists():
            print(f"⚠️ Fichier introuvable : {filepath}")
            continue
        items = extract_items_from_docx(p)
        for it in items:
            all_rows.append({
                "id": offset + it["local_id"],  # 1..700 via offsets 0,100,200,...
                "categorie": categorie,
                "question": it["question"],
                "reponse": it["reponse"],
            })
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.sort_values("id")
    return df

def build_bris_dataframe():
    p = Path(BRIS_FILE)
    if not p.exists():
        return None
    items = extract_items_from_docx(p)
    rows = [{"id": it["local_id"], "affirmation": it["question"], "reponse": it["reponse"]} for it in items]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("id")
    return df

if __name__ == "__main__":
    cat_df = build_categories_dataframe()
    print(f"✅ Catégories fusionnées : {len(cat_df)} cartes")
    bris_df = build_bris_dataframe()
    if bris_df is not None:
        print(f"✅ Bris d’égalité : {len(bris_df)} cartes")

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        if not cat_df.empty:
            cat_df.to_excel(writer, sheet_name="Categories", index=False)
        if bris_df is not None and not bris_df.empty:
            bris_df.to_excel(writer, sheet_name="Bris", index=False)

    print(f"💾 Export → {OUTPUT_XLSX}")
