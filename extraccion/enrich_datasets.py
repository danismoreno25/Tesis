#!/usr/bin/env python3
"""
Genera dos artefactos a partir de llm_cleaned_decisions.csv:

1. items_desde_txt_imputed.csv
   - Replica el dataset base con columnas adicionales para indicar si el precio fue imputado,
     la fuente del valor y el monto final utilizado.

2. items_augmented.csv
   - Produce variaciones textuales a partir de los productos con mejor calidad (keep) para
     facilitar el entrenamiento de un aumentador o modelos supervisados.
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

BASE_PATH = Path(__file__).resolve().parent
DECISIONS_PATH = BASE_PATH / "dataset" / "llm_cleaned_decisions.csv"
IMPUTED_PATH = BASE_PATH / "llm_artifacts" / "items_desde_txt_imputed.csv"
AUGMENTED_PATH = BASE_PATH / "llm_artifacts" / "items_augmented.csv"

AUX_FX_DIR = BASE_PATH.parent / "extraccion_variables_eda" / "dataset" / "txt_limpios"

COUNTRY_FILE_MAP = {
    "AR": "argentina",
    "BR": "brasil",
    "CL": "chile",
    "CO": "colombia",
    "CR": "costa_rica",
    "EC": None,
    "MX": "mexico",
    "PA": "panama",
    "PY": "paraguay",
    "PE": "peru",
    "US": None,
}

USD_PATTERN = re.compile(r"1\s*USD\s*=\s*([\d\.,\s]+)\s*([A-Z]{2,4})")


def load_decisions() -> pd.DataFrame:
    if not DECISIONS_PATH.exists():
        raise FileNotFoundError(f"No se encontró {DECISIONS_PATH}. Ejecuta generar_llm_outputs.py primero.")
    df = pd.read_csv(DECISIONS_PATH)
    if "price_amount" in df.columns:
        df["price_amount"] = pd.to_numeric(df["price_amount"], errors="coerce")
    if "country" not in df.columns:
        df["country"] = "unknown"
    df["country"] = df["country"].fillna("unknown").astype(str).str.upper()
    return df


def parse_decimal(value: str) -> float:
    clean = value.replace("\xa0", "").replace(" ", "")
    if clean.count(",") and clean.count("."):
        if clean.rfind(",") > clean.rfind("."):
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif clean.count(","):
        clean = clean.replace(",", ".")
    return float(clean)


def extract_fx_from_file(path: Path) -> float | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = text.replace("\xa0", " ")
    match = USD_PATTERN.search(text)
    if not match:
        return None
    try:
        return parse_decimal(match.group(1))
    except ValueError:
        return None


def load_fx_rates() -> Dict[str, Tuple[float, str]]:
    rates: Dict[str, Tuple[float, str]] = {}
    for country_code, name in COUNTRY_FILE_MAP.items():
        if not name:
            rates[country_code] = (1.0, "default_1usd")
            continue
        path = AUX_FX_DIR / f"{name}_cambio_dolar.txt"
        if not path.exists():
            rates[country_code] = (1.0, "missing_file")
            continue
        fx_value = extract_fx_from_file(path)
        if fx_value and fx_value > 0:
            rates[country_code] = (fx_value, f"from_{name}_cambio_dolar")
        else:
            rates[country_code] = (1.0, "missing_match")
    return rates


def attach_fx_columns(df: pd.DataFrame, fx_rates: Dict[str, Tuple[float, str]]) -> pd.DataFrame:
    fx_rate_list = []
    fx_source_list = []
    usd_values = []
    for _, row in df.iterrows():
        country = row.get("country", "unknown")
        country = str(country).upper() if country and country != "nan" else "UNKNOWN"
        fx_rate, source = fx_rates.get(country, (1.0, "default_1usd"))
        fx_rate_list.append(fx_rate)
        fx_source_list.append(source)
        price = row.get("price_amount")
        if pd.notna(price) and fx_rate > 0:
            usd_values.append(float(price) / fx_rate)
        else:
            usd_values.append(float("nan"))
    df = df.copy()
    df["fx_rate_local_per_usd"] = fx_rate_list
    df["fx_source"] = fx_source_list
    df["price_amount_usd"] = pd.Series(usd_values).round(4)
    return df


def compute_reference_stats(df: pd.DataFrame) -> Dict[str, Dict]:
    keep = df[
        (df["decision"] == "keep")
        & df["price_amount_usd"].notna()
        & (df["price_amount_usd"] > 0)
    ].copy()

    stats = {
        "category_country_mean": keep.groupby(["category_canonical", "country"])["price_amount_usd"].mean().to_dict(),
        "category_mean": keep.groupby("category_canonical")["price_amount_usd"].mean().to_dict(),
        "country_mean": keep.groupby("country")["price_amount_usd"].mean().to_dict(),
        "global_mean": float(keep["price_amount_usd"].mean()) if not keep.empty else None,
    }
    return stats


def impute_price(
    row: pd.Series,
    stats: Dict[str, Dict],
) -> Tuple[float, bool, str, float]:
    original_price = row["price_amount"]
    usd_price = row.get("price_amount_usd")
    fx_rate = row.get("fx_rate_local_per_usd") or 1.0
    if fx_rate <= 0:
        fx_rate = 1.0

    if pd.notna(original_price) and original_price > 0 and pd.notna(usd_price) and usd_price > 0:
        return float(original_price), False, "original", float(usd_price)

    category = row["category_canonical"]
    country = row["country"]

    cat_country_key = (category, country)
    cat_country_price = stats["category_country_mean"].get(cat_country_key)
    if cat_country_price and cat_country_price > 0:
        local = float(cat_country_price * fx_rate)
        return local, True, "category_country_mean", float(cat_country_price)

    cat_price = stats["category_mean"].get(category)
    if cat_price and cat_price > 0:
        local = float(cat_price * fx_rate)
        return local, True, "category_mean", float(cat_price)

    country_price = stats["country_mean"].get(country)
    if country_price and country_price > 0:
        local = float(country_price * fx_rate)
        return local, True, "country_mean", float(country_price)

    global_price = stats["global_mean"]
    if global_price and global_price > 0:
        local = float(global_price * fx_rate)
        return local, True, "global_mean", float(global_price)

    # Fallback: sin referencia (mantiene NaN)
    return float("nan"), False, "not_available", float("nan")


def build_imputed_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    stats = compute_reference_stats(df)
    results = df.apply(lambda row: impute_price(row, stats), axis=1, result_type="expand")
    results.columns = [
        "price_amount_filled",
        "price_is_imputed",
        "price_imputation_source",
        "price_amount_usd_filled",
    ]
    enriched = df.copy()
    for col in results.columns:
        enriched[col] = results[col]
    enriched["price_amount_filled"] = enriched["price_amount_filled"].round(2)
    enriched["price_amount_usd_filled"] = enriched["price_amount_usd_filled"].round(4)

    price_flag = enriched["price_is_imputed"].fillna(False).astype(int)
    source_series = enriched["price_imputation_source"].fillna("not_available")
    summary = {
        "total_rows": len(df),
        "imputed_rows": int(price_flag.sum()),
        "source_category_country": int((source_series == "category_country_mean").sum()),
        "source_category": int((source_series == "category_mean").sum()),
        "source_country": int((source_series == "country_mean").sum()),
        "source_global": int((source_series == "global_mean").sum()),
        "source_na": int((source_series == "not_available").sum()),
    }
    return enriched, summary


CONNECTORS = [
    "Aprovecha",
    "Encuentra",
    "Descubre",
    "Consigue",
    "Disfruta",
]

BENEFIT_INTROS = [
    "Ideal para",
    "Perfecto si buscas",
    "Pensado para",
    "Recomendado para",
    "Excelente opción cuando necesitas",
]


def clean_str(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_pick(values, default=""):
    seq = [v for v in values if isinstance(v, str) and v.strip()]
    return random.choice(seq) if seq else default


def format_currency(price: float, currency: str) -> str:
    if pd.isna(price):
        return ""
    if currency is None or (isinstance(currency, float) and pd.isna(currency)):
        currency_clean = ""
    else:
        currency_clean = str(currency).strip()
    upper = currency_clean.upper()
    if upper in {"USD", "US$", "US"}:
        prefix = "US$"
    elif upper in {"MXN", "MEX", "MX"}:
        prefix = "$"
    elif upper in {"BRL", "R$", "BR"}:
        prefix = "R$"
    elif upper in {"PEN", "S/"}:
        prefix = "S/"
    elif upper in {"ARS", "AR"}:
        prefix = "$"
    else:
        prefix = currency_clean or "$"
    return f"{prefix}{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_variations(row: pd.Series, max_variations: int = 2) -> list[dict]:
    variations = []
    base_price = row["price_amount_filled"]
    if pd.isna(base_price) or base_price <= 0:
        return variations

    price_text = format_currency(base_price, row.get("price_currency") or row.get("currency_raw"))
    country = clean_str(row.get("country") or "desconocido").upper()
    product = clean_str(row.get("product_name") or row.get("title") or "")
    brand = clean_str(row.get("brand") or "")
    unit = clean_str(row.get("unit") or "")
    category = clean_str(row.get("category_canonical") or "")
    description = safe_pick(
        [
            clean_str(row.get("description_text")),
            clean_str(row.get("information_text")),
            clean_str(row.get("features_text")),
        ],
        default="",
    )
    benefits = safe_pick(
        [
            clean_str(row.get("benefits_text")),
            clean_str(row.get("details_text")),
            clean_str(row.get("other_sections")),
        ],
        default="",
    )

    connector_choices = random.sample(CONNECTORS, k=min(len(CONNECTORS), max_variations))
    for connector in connector_choices:
        text_parts = [
            f"{connector} {product}",
            f"de {brand}" if brand else "",
            f"({unit})" if unit else "",
            f"por {price_text}",
            f"en {country}" if country else "",
        ]
        headline = " ".join(part for part in text_parts if part).strip()

        benefit_intro = safe_pick(BENEFIT_INTROS, default="")
        benefit_text = f"{benefit_intro} {benefits.strip()}" if benefit_intro and benefits else benefits

        body_parts = [
            description.strip(),
            benefit_text.strip(),
        ]
        body = " ".join(part for part in body_parts if part)

        variations.append(
            {
                "source_id": row["source_id"],
                "product_name": product,
                "brand": brand,
                "unit": unit,
                "category_canonical": category,
                "country": country,
                "price_text": price_text,
                "price_amount": base_price,
                "price_currency": row.get("price_currency"),
                "generated_text": f"{headline}. {body}".strip(),
                "generation_origin": row.get("price_imputation_source"),
                "base_decision": row.get("decision"),
            }
        )
    return variations


def build_augmented_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    eligible = df[
        (df["price_amount_filled"].notna())
        & (df["price_amount_filled"] > 0)
        & (df["category_canonical"] != "sin_categoria")
    ].copy()

    rows = []
    for _, row in eligible.iterrows():
        rows.extend(generate_variations(row, max_variations=2))

    augmented = pd.DataFrame(rows)
    summary = {
        "eligible_rows": len(eligible),
        "generated_rows": len(augmented),
    }
    return augmented, summary


def main():
    random.seed(42)
    df = load_decisions()
    fx_rates = load_fx_rates()
    df = attach_fx_columns(df, fx_rates)

    imputed_df, imputed_summary = build_imputed_dataset(df)
    imputed_df.to_csv(IMPUTED_PATH, index=False)

    augmented_df, augmented_summary = build_augmented_dataset(imputed_df)
    augmented_df.to_csv(AUGMENTED_PATH, index=False)

    print("✅ Archivo guardado:", IMPUTED_PATH.relative_to(BASE_PATH.parent))
    print("   Filas totales:", imputed_summary["total_rows"])
    print("   Filas con precio imputado:", imputed_summary["imputed_rows"])
    print("     Por categoría-país:", imputed_summary["source_category_country"])
    print("     Solo categoría:", imputed_summary["source_category"])
    print("     Solo país:", imputed_summary["source_country"])
    print("     Media global:", imputed_summary["source_global"])
    print("     Sin referencia disponible:", imputed_summary["source_na"])
    print("   Columnas clave nuevas: price_amount_usd, price_amount_usd_filled, fx_rate_local_per_usd, fx_source.")

    print("✅ Archivo guardado:", AUGMENTED_PATH.relative_to(BASE_PATH.parent))
    print("   Filas elegibles para aumentar:", augmented_summary["eligible_rows"])
    print("   Frases generadas:", augmented_summary["generated_rows"])


if __name__ == "__main__":
    main()
