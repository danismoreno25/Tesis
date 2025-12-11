#!/usr/bin/env python3
"""
Benchmark de carga para la imputación de precios.

Genera un dataset sintético con valores faltantes y mide:
- Tiempo total de imputación.
- Cantidad de filas imputadas.
- Throughput (filas/segundo).

Cómo ejecutar:
    python tests/benchmark_imputation.py --rows 5000
"""

from __future__ import annotations

import argparse
import random
import time
from typing import Dict, Tuple

import numpy as np
import pandas as pd

# Asegura que se pueda importar el paquete local "extraccion"
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extraccion.enrich_datasets import build_imputed_dataset


def build_synthetic_df(n_rows: int, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    countries = ["MX", "BR", "AR"]
    categories = ["arroz", "leche", "aceite"]
    currencies = {"MX": "MXN", "BR": "BRL", "AR": "ARS"}
    fx_map: Dict[str, Tuple[float, str]] = {"MX": (16.5, "synthetic"), "BR": (5.1, "synthetic"), "AR": (900.0, "synthetic")}

    rows = []
    for i in range(n_rows):
        country = rng.choice(countries)
        category = rng.choice(categories)
        currency = currencies[country]
        fx, _ = fx_map[country]

        # 60% con precio válido, 40% faltante
        if rng.random() < 0.6:
            price_local = round(np_rng.normal(30, 10), 2)
            price_local = max(price_local, 1.0)
        else:
            price_local = np.nan

        price_usd = price_local / fx if not np.isnan(price_local) else np.nan

        rows.append(
            {
                "source_id": i,
                "country": country,
                "category_canonical": category,
                "price_amount": price_local,
                "price_amount_usd": price_usd,
                "fx_rate_local_per_usd": fx,
                "fx_source": "synthetic",
                "price_currency": currency,
                "decision": "keep",
            }
        )

    return pd.DataFrame(rows)


def run_benchmark(n_rows: int) -> None:
    df = build_synthetic_df(n_rows)

    start = time.perf_counter()
    imputed_df, summary = build_imputed_dataset(df)
    elapsed = time.perf_counter() - start

    total = summary["total_rows"]
    imputed = summary["imputed_rows"]
    throughput = total / elapsed if elapsed > 0 else float("inf")

    print("=== Benchmark imputación ===")
    print(f"Filas totales:        {total}")
    print(f"Filas imputadas:      {imputed}")
    print(f"Tiempo total (s):     {elapsed:.3f}")
    print(f"Throughput (filas/s): {throughput:.1f}")

    sources = imputed_df["price_imputation_source"].fillna("not_available").value_counts()
    print("\nFuentes de imputación:")
    for src, count in sources.items():
        print(f"  {src}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark de carga para imputación de precios.")
    parser.add_argument("--rows", type=int, default=5000, help="Número de filas sintéticas a procesar (default: 5000).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_benchmark(args.rows)
