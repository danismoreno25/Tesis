#!/usr/bin/env python3
"""
Cruza productos_para_db.csv con edaSisPricingNuevo.xlsx para rellenar
país y marca basados en la información original del Excel.

Salida: extraccion/dataset/productos_para_db_imputed.csv

No requiere instalar unidecode; usa unicodedata para normalizar acentos.
"""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd

BASE_PATH = Path(__file__).resolve().parent
EXCEL_PATH = BASE_PATH.parent / "edaSisPricingNuevo.xlsx"
CSV_PATH = BASE_PATH / "dataset" / "productos_para_db.csv"
OUTPUT_PATH = BASE_PATH / "dataset" / "productos_para_db_imputed.csv"


def normalize_text(text: Optional[str]) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def load_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}.")
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    required = {"Pais", "Producto", "Nombre marca"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {missing}")
    df = df.copy()
    df["clave_match"] = (
        df["Pais"].apply(normalize_text)
        + " | "
        + df["Producto"].apply(normalize_text)
        + " | "
        + df["Nombre marca"].apply(normalize_text)
    )
    return df


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}.")
    df = pd.read_csv(path)
    for col in ["country", "product_name", "brand"]:
        if col not in df.columns:
            raise ValueError(f"El CSV no contiene la columna requerida '{col}'.")
    df = df.copy()
    df["clave_match"] = (
        df["country"].apply(normalize_text)
        + " | "
        + df["product_name"].apply(normalize_text)
        + " | "
        + df["brand"].apply(normalize_text)
    )
    return df


def main():
    parser = argparse.ArgumentParser(description="Cruza el Excel original con productos_para_db.csv.")
    parser.add_argument("--excel", default=EXCEL_PATH, help="Ruta al Excel edaSisPricingNuevo.xlsx.")
    parser.add_argument("--csv", default=CSV_PATH, help="Ruta al CSV productos_para_db.csv.")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Ruta de salida.")
    args = parser.parse_args()

    excel_df = load_excel(Path(args.excel))
    csv_df = load_csv(Path(args.csv))

    merged = csv_df.merge(
        excel_df[["clave_match", "Pais", "Nombre marca"]],
        on="clave_match",
        how="left",
        suffixes=("", "_excel"),
    )

    merged["country"] = merged["country"].fillna(merged["Pais"])
    merged["brand"] = merged["brand"].fillna(merged["Nombre marca"])

    merged = merged.drop(columns=["clave_match", "Pais", "Nombre marca"])
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)

    matches = merged["brand"].notna().sum()
    print(f"✅ Archivo guardado: {Path(args.output).relative_to(BASE_PATH.parent)}")
    print("Coincidencias (brand no nulo):", matches)


if __name__ == "__main__":
    main()
