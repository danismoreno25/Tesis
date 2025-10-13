
import csv
import json
import re
import unicodedata
from typing import Dict, Any, List, Optional
import os

DEFAULT_CONFIG = {
    "categories": [
        "aceite vegetal", "arroz", "atun", "azucar", "banano", "cafe",
        "cebolla", "cerveza", "frijoles", "harina de trigo", "huevos",
        "leche", "manzanas", "pan", "papa", "pasta seca", "pollo entero",
        "queso blanco", "refresco de cola", "tomates"
    ],
    "synonyms": {
        "leche liquida": "leche",
        "leche líquida": "leche",
        "atun en lata": "atun",
        "atún en lata": "atun",
        "pan de molde": "pan",
        "cebollas": "cebolla",
        "papas": "papa",
        "café": "cafe",
        "café molido": "cafe",
        "azúcar": "azucar",
        "bananos": "banano",
        "aceite vegetal": "aceite",
        "huevos": "huevo",
        "fríjoles": "frijoles"
    },
    "exclude_keywords": [
        "gift card", "tarjeta regalo", "servicio", "instalación", "membresía",
        "recarga", "garantía", "warranty", "accesorio", "funda", "repuesto"
    ]
}

def try_load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # pip install pyyaml
    except ImportError:
        print("[WARN] PyYAML no instalado; usando configuración por defecto.")
        return DEFAULT_CONFIG
    if not os.path.exists(path):
        print(f"[WARN] No se encontró {path}; usando configuración por defecto.")
        return DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    cfg = DEFAULT_CONFIG.copy()
    cfg.update({k: data.get(k, cfg.get(k)) for k in ["categories", "synonyms", "exclude_keywords"]})
    return cfg

def strip_accents(s: str) -> str:
    s_norm = unicodedata.normalize("NFD", s)
    s_no_acc = "".join(ch for ch in s_norm if unicodedata.category(ch) != 'Mn')
    return s_no_acc

def normalize_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    s = strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s

class Canonicalizer:
    def __init__(self, config: Dict[str, Any]):
        self.categories = [normalize_text(c) for c in config.get("categories", [])]
        raw_syn = config.get("synonyms", {})
        self.synonyms = {normalize_text(k): normalize_text(v) for k, v in raw_syn.items()}
        self.exclude_keywords = [normalize_text(k) for k in config.get("exclude_keywords", [])]

    def canonical_category_from_text(self, text: str) -> Optional[str]:
        t = normalize_text(text)
        for syn, canon in self.synonyms.items():
            if re.search(rf"(?:^|\W){re.escape(syn)}(?:$|\W)", t):
                return canon
        for cat in self.categories:
            if re.search(rf"(?:^|\W){re.escape(cat)}(?:$|\W)", t):
                return cat
        return None

    def is_excluded(self, text: str) -> bool:
        t = normalize_text(text)
        return any(kw in t for kw in self.exclude_keywords)

SCHEMA_JSON = {"type":"object"}  # guía (omitida en la ejecución heurística)

PROMPT_TEMPLATE = """
TITLE: {title}
DESCRIPTION: {description}
BREADCRUMBS: {breadcrumbs}
PRICE_RAW: {price_raw}
CURRENCY_RAW: {currency_raw}
URL: {url}
SELLER: {seller}
AVAILABILITY: {availability}
PAIS: {country}
"""

def build_prompt(row: Dict[str, Any]) -> str:
    return PROMPT_TEMPLATE.format(
        title=row.get("title",""),
        description=row.get("description",""),
        breadcrumbs=row.get("breadcrumbs",""),
        price_raw=row.get("price_raw",""),
        currency_raw=row.get("currency_raw",""),
        url=row.get("url",""),
        seller=row.get("seller",""),
        availability=row.get("availability",""),
        country=row.get("country",""),
    )

def llm_call(prompt: str, canon: Canonicalizer) -> Dict[str, Any]:
    # Heurística para funcionar sin LLM real
    import re
    title = re.search(r"TITLE: (.*)", prompt).group(1)
    description = re.search(r"DESCRIPTION: (.*)", prompt).group(1)
    breadcrumbs = re.search(r"BREADCRUMBS: (.*)", prompt).group(1)
    price_raw = re.search(r"PRICE_RAW: (.*)", prompt).group(1)
    currency_raw = re.search(r"CURRENCY_RAW: (.*)", prompt).group(1)
    seller = re.search(r"SELLER: (.*)", prompt).group(1)
    availability = re.search(r"AVAILABILITY: (.*)", prompt).group(1)
    country = re.search(r"PAIS: (.*)", prompt).group(1)

    text = " ".join([title, description, breadcrumbs])
    reasons = []
    if canon.is_excluded(text):
        return {
            "normalized": {"name": title[:120], "brand": None, "variant": None, "category": "descartado",
                           "size_value": None, "size_unit": None, "pack_count": None},
            "pricing": {"price": float(price_raw) if price_raw.strip() else 0.0, "currency": currency_raw or "COP", "promo_flag": False},
            "meta": {"seller": seller, "availability": availability, "country": country, "source_url": None, "timestamp": ""},
            "judgement": {"match_score": 0.1, "keep_or_discard": "discard", "reasons": ["excluded_keyword"]}
        }

    cat = canon.canonical_category_from_text(text) or "sin_categoria"
    if cat == "sin_categoria": reasons.append("no_category_detected")
    try:
        price = float(price_raw)
    except:
        price = 0.0
        reasons.append("price_parse_failed")

    keep_or_discard = "keep" if (cat in canon.categories and price > 0) else "discard"
    if keep_or_discard == "discard" and cat in canon.categories:
        reasons.append("price<=0")

    return {
        "normalized": {"name": title[:120], "brand": None, "variant": None, "category": cat,
                       "size_value": None, "size_unit": None, "pack_count": None},
        "pricing": {"price": price, "currency": currency_raw or "COP", "promo_flag": False},
        "meta": {"seller": seller, "availability": availability, "country": country, "source_url": None, "timestamp": ""},
        "judgement": {"match_score": 0.6 if cat in canon.categories else 0.3, "keep_or_discard": keep_or_discard,
                      "reasons": reasons or ["heuristic_default"]}
    }

def process_csv(input_csv: str, output_jsonl: str, output_csv: str, config_path: str):
    cfg = try_load_yaml(config_path)
    canon = Canonicalizer(cfg)

    out_rows: List[Dict[str, Any]] = []
    with open(input_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prompt = build_prompt(row)
            data = llm_call(prompt, canon)
            decision = "keep" if data.get("judgement", {}).get("keep_or_discard") == "keep" else "discard"
            out_rows.append({
                **row,
                "category_canonical": data["normalized"]["category"],
                "decision": decision,
                "match_score": data["judgement"]["match_score"],
                "reasons": ";".join(data["judgement"]["reasons"]),
            })

    import pandas as pd
    df = pd.DataFrame(out_rows)
    df.to_csv(output_csv, index=False)

    with open(output_jsonl, "w", encoding="utf-8") as jf:
        for r in out_rows:
            jf.write(json.dumps(r, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", default="../data/llm_cleaning_template.csv")
    ap.add_argument("--out_csv", default="../data/llm_cleaned_decisions.csv")
    ap.add_argument("--out_jsonl", default="../data/llm_cleaned_decisions.jsonl")
    ap.add_argument("--config", default="../config/categories.yaml")
    args = ap.parse_args()
    process_csv(args.in_csv, args.out_jsonl, args.out_csv, args.config)