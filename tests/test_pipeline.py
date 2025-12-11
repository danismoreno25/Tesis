import sys
from pathlib import Path
import sqlite3

import pytest
import math

# Intentamos forzar el uso de site-packages del entorno local
ROOT = Path(__file__).resolve().parents[1]
venv_site = ROOT / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.append(str(venv_site))

pd = pytest.importorskip("pandas", reason="Instala pandas (y dependencias) para ejecutar estas pruebas.")

# Asegura que el repo raíz esté en el path para importar módulos sin empaquetar
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extraccion.enrich_datasets import (
    parse_decimal,
    attach_fx_columns,
    impute_price,
    build_imputed_dataset,
    generate_variations,
)


# ---------------------------
# Limpieza / parsing
# ---------------------------

def test_parse_decimal_comma_and_dot():
    """Debe interpretar correctamente valores con coma como decimal."""
    assert parse_decimal("5,448") == pytest.approx(5.448)
    assert parse_decimal("1.234,50") == pytest.approx(1234.50)


def test_clean_fx_attach():
    """attach_fx_columns debe aplicar la tasa FX y calcular USD."""
    df = pd.DataFrame([{"price_amount": 10.0, "country": "BR"}])
    fx_rates = {"BR": (5.0, "test_fx")}
    out = attach_fx_columns(df, fx_rates)
    assert out.loc[0, "fx_rate_local_per_usd"] == 5.0
    assert out.loc[0, "price_amount_usd"] == pytest.approx(2.0)


# ---------------------------
# Imputación de precios
# ---------------------------

def test_impute_price_with_stats():
    """Imputa usando media categoría-país y respeta el FX."""
    stats = {
        "category_country_mean": {("arroz", "AR"): 1.5},  # USD
        "category_mean": {},
        "country_mean": {},
        "global_mean": None,
    }
    row = pd.Series(
        {
            "price_amount": float("nan"),
            "price_amount_usd": float("nan"),
            "fx_rate_local_per_usd": 100,  # 1 USD = 100 ARS
            "category_canonical": "arroz",
            "country": "AR",
        }
    )
    local, is_imp, source, usd_val = impute_price(row, stats)
    assert is_imp is True
    assert source == "category_country_mean"
    assert local == pytest.approx(150.0)  # 1.5 USD * 100 ARS
    assert usd_val == pytest.approx(1.5)


def test_impute_price_without_stats():
    """Sin estadísticas y precio NaN, no debe imputar."""
    stats = {"category_country_mean": {}, "category_mean": {}, "country_mean": {}, "global_mean": None}
    row = pd.Series(
        {
            "price_amount": float("nan"),
            "price_amount_usd": float("nan"),
            "fx_rate_local_per_usd": 1.0,
            "category_canonical": "arroz",
            "country": "AR",
        }
    )
    local, is_imp, source, usd_val = impute_price(row, stats)
    assert is_imp is False
    assert source == "not_available"
    assert math.isnan(local)
    assert math.isnan(usd_val)


def test_build_imputed_dataset_summary():
    """Cuenta filas imputadas en build_imputed_dataset."""
    df = pd.DataFrame(
        [
            {"decision": "keep", "price_amount": 10, "price_amount_usd": 2, "category_canonical": "pan", "country": "CO"},
            {"decision": "keep", "price_amount": float("nan"), "price_amount_usd": float("nan"), "category_canonical": "pan", "country": "CO"},
        ]
    )
    enriched, summary = build_imputed_dataset(df)
    assert summary["total_rows"] == 2
    assert summary["imputed_rows"] == 1
    assert summary["source_category_country"] == 1


# ---------------------------
# Aumentación de datos
# ---------------------------

def test_generate_variations_ok():
    row = pd.Series(
        {
            "source_id": 1,
            "product_name": "Arroz Extra",
            "brand": "MarcaX",
            "unit": "1kg",
            "category_canonical": "arroz",
            "country": "CO",
            "price_amount_filled": 12.5,
            "price_currency": "COP",
            "decision": "keep",
            "price_imputation_source": "original",
            "description_text": "Arroz blanco",
            "information_text": "",
            "features_text": "",
        }
    )
    variations = generate_variations(row, max_variations=1)
    assert len(variations) == 1
    assert "Arroz Extra" in variations[0]["generated_text"]
    assert variations[0]["price_amount"] == pytest.approx(12.5)


def test_generate_variations_skip_when_no_price():
    row = pd.Series({"source_id": 1, "product_name": "Arroz Extra", "price_amount_filled": 0})
    assert generate_variations(row) == []


# ---------------------------
# Inserción en BD (simulada)
# ---------------------------

def test_db_insert_success():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO products (id, name) VALUES (?, ?)", (1, "Producto A"))
    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1


def test_db_insert_failure_unique():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO products (id, name) VALUES (?, ?)", (1, "Producto A"))
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO products (id, name) VALUES (?, ?)", (1, "Duplicado"))
    conn.close()
