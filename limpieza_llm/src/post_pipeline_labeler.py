
import argparse
from pathlib import Path
import pandas as pd
import re

def detect_lang(text: str) -> str:
    if not text or not isinstance(text, str) or len(text.strip()) < 20:
        return "unknown"
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        t = text.lower()
        if any(w in t for w in [" o ", " el ", " la ", " de ", " y ", " para ", "precio", "agregar", "descripción", "especificaciones"]):
            return "es"
        if any(w in t for w in ["ção", "ções", "ão ", "ões ", "preço", "produto", "adicionar"]):
            return "pt"
        return "unknown"

def is_cookie_or_security(title: str, description: str) -> bool:
    blob = f"{title} {description}".lower()
    return any(kw in blob for kw in [
        "este sitio web utiliza cookies", "política de cookies", "cloudflare", "verificar que usted es un ser humano",
        "captcha", "ray id", "comprobar que eres humano", "verificación de seguridad"
    ])

def usability_label(row) -> str:
    decision = str(row.get("decision", "")).lower()
    category = str(row.get("category_canonical", ""))
    reasons = str(row.get("reasons", "")).lower()
    price_raw = row.get("price_raw", "")
    try:
        price = float(price_raw)
    except Exception:
        price = 0.0

    if is_cookie_or_security(str(row.get("title","")), str(row.get("description",""))):
        return "para_nada_usables"

    if decision == "discard" or category in ("", "sin_categoria", "descartado"):
        return "para_nada_usables"

    if price <= 0:
        return "para_nada_usables"

    partial_signals = ["no_category_detected", "price_parse_failed", "low_score", "heuristic_default"]
    if any(sig in reasons for sig in partial_signals):
        return "medianamente_usables"

    return "usables"

def make_feature_vector(df_keep: pd.DataFrame) -> pd.DataFrame:
    import numpy as np
    out = df_keep.copy()
    out["price_num"] = pd.to_numeric(out["price_raw"], errors="coerce").fillna(0.0)
    out["log_price"] = np.log1p(out["price_num"])
    out["title_len"] = out["title"].fillna("").astype(str).str.len()
    def has_brand(title: str) -> int:
        if not isinstance(title, str): return 0
        return 1 if re.search(r"\b[A-ZÁÉÍÓÚÜÑ]{3,}\b", title) else 0
    out["has_brand"] = out["title"].apply(has_brand)
    out["tokens_count"] = out["description"].fillna("").astype(str).str.split().apply(len)
    return out[["title","category_canonical","price_raw","seller","country","log_price","title_len","has_brand","tokens_count"]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True, help="CSV de entrada (salida del pipeline)")
    ap.add_argument("--out_dir", required=True, help="Carpeta de salida (se crearán varios CSVs)")
    args = ap.parse_args()

    in_csv = Path(args.in_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_csv)

    langs = []
    is_spanish_native = []
    needs_translation = []
    for _, r in df.iterrows():
        text_for_lang = f"{str(r.get('title',''))}. {str(r.get('description',''))}"
        lang = detect_lang(text_for_lang)
        langs.append(lang)
        is_spanish_native.append(lang == "es")
        needs_translation.append(lang in ("pt","en","fr","it","de","unknown"))
    df["lang"] = langs
    df["is_spanish_native"] = is_spanish_native
    df["needs_translation"] = needs_translation

    df["usability"] = df.apply(usability_label, axis=1)

    master_path = out_dir / "llm_labeled_master.csv"
    df.to_csv(master_path, index=False, encoding="utf-8")
    print(f"[OK] Guardado maestro: {master_path} ({len(df)} filas)")

    df_usable = df[df["usability"] == "usables"].copy()
    df_partial = df[df["usability"] == "medianamente_usables"].copy()
    df_bad = df[df["usability"] == "para_nada_usables"].copy()

    df_usable.to_csv(out_dir / "llm_usables.csv", index=False, encoding="utf-8")
    df_partial.to_csv(out_dir / "llm_medianamente_usables.csv", index=False, encoding="utf-8")
    df_bad.to_csv(out_dir / "llm_para_nada_usables.csv", index=False, encoding="utf-8")

    print(f"[OK] Usables: {len(df_usable)} | Medianamente: {len(df_partial)} | No usables: {len(df_bad)}")

    if len(df_usable) > 0:
        feats = make_feature_vector(df_usable)
        feats_path = out_dir / "llm_feature_vectors.csv"
        feats.to_csv(feats_path, index=False, encoding="utf-8")
        print(f"[OK] Vectores de características: {feats_path} ({len(feats)} filas)")
    else:
        print("[INFO] No hay usables aún; no se generaron vectores.")

    print("\n[INFO] Traducción: usa needs_translation==True para decidir qué pasar por una API.")
    print("Sugerencias de API: Google Cloud Translate, DeepL, LibreTranslate (self-hosted).")

if __name__ == "__main__":
    main()