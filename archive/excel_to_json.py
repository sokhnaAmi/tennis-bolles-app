# pip install pandas openpyxl
import pandas as pd
from pathlib import Path
import json

EXCEL = "jeu_bolles.xlsx"          # ton fichier Excel
SHEET_CATS = "Categories"          # feuilles telles que dans ton fichier
SHEET_BRIS = "Bris"
OUT = "data.json"                  # sortie pour l'app

def norm(s):
    return ("" if pd.isna(s) else str(s)).strip()

def main():
    x = pd.ExcelFile(EXCEL)
    # --- Catégories ---
    cats = []
    if SHEET_CATS in x.sheet_names:
        dfc = pd.read_excel(EXCEL, sheet_name=SHEET_CATS, dtype=str)
        for _, r in dfc.iterrows():
            cats.append({
                "id": int(float(r.get("id","0") or 0)),
                #"categorie": norm(r.get("categorie","")),
                "question": norm(r.get("question","")),
                "reponse": norm(r.get("reponse","")),
            })
        cats.sort(key=lambda d: d["id"])
    # --- Bris ---
    bris = []
    if SHEET_BRIS in x.sheet_names:
        dfb = pd.read_excel(EXCEL, sheet_name=SHEET_BRIS, dtype=str)
        for _, r in dfb.iterrows():
            bris.append({
                "id": int(float(r.get("id","0") or 0)),
                "affirmation": norm(r.get("affirmation","")),
                "reponse": norm(r.get("reponse","")),
            })
        bris.sort(key=lambda d: d["id"])

    data = {"categories": cats, "bris": bris}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"OK → {OUT} ({len(cats)} catégories, {len(bris)} bris)")

if __name__ == "__main__":
    main()
