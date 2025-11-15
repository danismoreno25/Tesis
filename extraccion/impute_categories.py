#!/usr/bin/env python3
"""
Imputación de categorías usando un clasificador Multinomial Naive Bayes implementado a mano
con bolsas de palabras (n-gramas simples).

Genera: extraccion/dataset/llm_cleaned_decisions_cat_imputed.csv
Columnas nuevas:
    - category_model_confidence (probabilidad posterior máxima)
    - category_canonical_imputed (categoría sugerida)
    - category_is_imputed (bool)
    - category_effective (categoría final considerando la imputación)
    - decision_imputed (decision original o keep_imputed si ahora cumple requisitos)

Algoritmo: Multinomial Naive Bayes con suavizado de Laplace. Referencia:
    Manning, Raghavan & Schütze. Introduction to Information Retrieval. Cambridge 2008.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

BASE_PATH = Path(__file__).resolve().parent
DECISIONS_PATH = BASE_PATH / "dataset" / "llm_cleaned_decisions.csv"
OUTPUT_PATH = BASE_PATH / "dataset" / "llm_cleaned_decisions_cat_imputed.csv"

TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]{2,}")


def tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text.lower())


def build_text(row: pd.Series) -> str:
    parts = [
        row.get("product_name", ""),
        row.get("title", ""),
        row.get("description", ""),
        row.get("information_text", ""),
        row.get("description_text", ""),
        row.get("features_text", ""),
        row.get("specifications_text", ""),
        row.get("benefits_text", ""),
        row.get("details_text", ""),
        row.get("other_sections", ""),
        row.get("unit", ""),
        row.get("brand", ""),
    ]
    return " ".join(str(p) for p in parts if isinstance(p, str))


def load_dataset() -> pd.DataFrame:
    if not DECISIONS_PATH.exists():
        raise FileNotFoundError(f"No se encontró {DECISIONS_PATH}. Ejecuta generar_llm_outputs.py primero.")
    df = pd.read_csv(DECISIONS_PATH)
    df["combined_text"] = df.apply(build_text, axis=1).fillna("").str.strip()
    return df


def train_naive_bayes(df: pd.DataFrame, min_len: int = 5):
    train_df = df[(df["category_canonical"].notna()) & (df["category_canonical"] != "sin_categoria")]
    train_df = train_df[train_df["combined_text"].str.len() > min_len]
    if train_df.empty:
        raise RuntimeError("No hay datos etiquetados suficientes para entrenar el modelo.")

    category_token_counts: Dict[str, Counter] = defaultdict(Counter)
    category_totals: Dict[str, int] = defaultdict(int)
    doc_counts: Dict[str, int] = defaultdict(int)
    vocab = set()

    for _, row in train_df.iterrows():
        category = row["category_canonical"]
        tokens = tokenize(row["combined_text"])
        if not tokens:
            continue
        category_token_counts[category].update(tokens)
        category_totals[category] += len(tokens)
        doc_counts[category] += 1
        vocab.update(tokens)

    total_docs = sum(doc_counts.values())
    priors = {cat: math.log(doc_counts[cat] / total_docs) for cat in doc_counts}
    vocab_size = len(vocab)
    alpha = 1.0  # Laplace smoothing

    model = {
        "priors": priors,
        "token_counts": category_token_counts,
        "totals": category_totals,
        "vocab_size": vocab_size,
        "alpha": alpha,
        "categories": list(category_token_counts.keys()),
        "doc_counts": doc_counts,
        "total_docs": total_docs,
    }
    return model


def predict_naive_bayes(model, text: str) -> Tuple[str, float]:
    tokens = tokenize(text)
    if not tokens:
        return "sin_categoria", 0.0

    priors = model["priors"]
    token_counts = model["token_counts"]
    totals = model["totals"]
    vocab_size = model["vocab_size"]
    alpha = model["alpha"]

    best_cat = "sin_categoria"
    log_values = []

    for cat, prior_log in priors.items():
        log_prob = prior_log
        total_tokens = totals[cat]
        for token in tokens:
            count = token_counts[cat][token]
            log_prob += math.log((count + alpha) / (total_tokens + alpha * vocab_size))
        log_values.append((cat, log_prob))

    if not log_values:
        return "sin_categoria", 0.0

    max_log = max(val for _, val in log_values)
    denom = sum(math.exp(val - max_log) for _, val in log_values)
    probs = {cat: math.exp(val - max_log) / denom for cat, val in log_values}
    best_cat = max(probs, key=probs.get)
    confidence = probs[best_cat]
    return best_cat, confidence


def apply_imputation(df: pd.DataFrame, model, threshold: float) -> pd.DataFrame:
    df = df.copy()
    df["category_model_confidence"] = 0.0
    df["category_canonical_imputed"] = ""
    df["category_is_imputed"] = False
    df["category_effective"] = df["category_canonical"]

    mask_candidates = (df["category_canonical"] == "sin_categoria") & (df["combined_text"].str.len() > 5)

    for idx in df[mask_candidates].index:
        text = df.at[idx, "combined_text"]
        pred_category, conf = predict_naive_bayes(model, text)
        df.at[idx, "category_model_confidence"] = conf
        if pred_category != "sin_categoria" and conf >= threshold:
            df.at[idx, "category_canonical_imputed"] = pred_category
            df.at[idx, "category_is_imputed"] = True
            df.at[idx, "category_effective"] = pred_category

    def recompute_decision(row):
        if "excluded_keyword" in str(row.get("reasons", "")):
            return row["decision"]
        price = row.get("price_amount_filled", row.get("price_amount"))
        if pd.notna(price) and price > 0 and row["category_effective"] != "sin_categoria":
            if row["decision"] == "keep":
                return "keep"
            return "keep_imputed"
        return row["decision"]

    df["decision_imputed"] = df.apply(recompute_decision, axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(description="Imputa categorías con Naive Bayes (sin dependencias externas).")
    parser.add_argument("--threshold", type=float, default=0.6, help="Confianza mínima (0-1) para aceptar la imputación.")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Ruta de salida del CSV resultante.")
    args = parser.parse_args()

    df = load_dataset()
    model = train_naive_bayes(df)
    info = {
        "categorias_entrenadas": model["categories"],
        "documentos_entrenamiento": model["total_docs"],
        "tokens_vocabulario": model["vocab_size"],
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))

    result_df = apply_imputation(df, model, threshold=args.threshold)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"✅ Archivo guardado: {output_path.relative_to(BASE_PATH.parent)}")
    print("   Filas imputadas:", int(result_df["category_is_imputed"].sum()))
    print("   Columnas nuevas: category_model_confidence, category_canonical_imputed, category_effective, decision_imputed.")


if __name__ == "__main__":
    main()
