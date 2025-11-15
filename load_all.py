import os
from collections import defaultdict

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# 1. CONFIGURACIÓN BÁSICA
# ---------------------------------------------------------------------
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)

# Ruta del CSV maestro
CSV_PATH = "productos_para_db_imputed.csv"  # ajusta si está en otra carpeta

# ---------------------------------------------------------------------
# 2. CONFIGURA ESTOS NOMBRES DE COLUMNA SEGÚN TU CSV
#    Abre productos_para_db_imputed.csv y verifica que coincidan
# ---------------------------------------------------------------------
COL_RETAILER = "retailer"            # ej. "retailer" o "seller" o similar
COL_RETAILER_COUNTRY = "country"     # ej. "country_code" / "pais_venta"

COL_CATEGORY_RAW = "category_raw"    # categoría original del sitio
COL_CATEGORY_CANON = "category"      # categoría canónica / limpia
COL_CATEGORY_IS_IMPUTED = "category_is_imputed"  # True/False si existe (si no, déjalo None)

COL_PRODUCT_NAME = "product_name"    # nombre canónico del producto
COL_BRAND = "brand"                  # marca
COL_UNIT = "unit"                    # contenido/neto (ej. "5Kg")
COL_PRODUCT_COUNTRY = "country"      # puedes reutilizar el mismo que retailer country

COL_PRICE_LOCAL = "price_local"      # precio en moneda local
COL_CURRENCY = "currency"            # código de moneda (BRL, COP, MXN...)
COL_PRICE_USD = "price_usd"          # precio convertido a USD
COL_FX = "fx_rate_local_per_usd"     # tasa de cambio usada

COL_PRICE_IS_IMPUTED = "price_is_imputed"   # True/False si existe
COL_PRICE_DECISION = "decision"             # "keep", "drop", etc.
COL_PRICE_REASON = "reason"                 # texto con la razón

# Si alguna de estas columnas no existe aún en tu CSV,
# puedes comentar la línea o poner None y ajustar más adelante.

# ---------------------------------------------------------------------
# 3. HELPERS
# ---------------------------------------------------------------------
def get_dataframe():
    print(f"Leyendo CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"Filas leídas: {len(df)}")
    return df


def load_retailers(df, conn):
    """
    Inserta retailers únicos en pricing.retailers y devuelve
    un dict (nombre, pais) -> retailer_id
    """
    print("\n=== Cargando retailers ===")
    sub = df[[COL_RETAILER, COL_RETAILER_COUNTRY]].drop_duplicates()

    # Leer retailers existentes
    existing = conn.execute(text("""
        SELECT retailer_id, nombre, pais
        FROM pricing.retailers
    """)).fetchall()
    retailer_map = {(row.nombre, row.pais): row.retailer_id for row in existing}

    inserted = 0
    for _, row in sub.iterrows():
        key = (row[COL_RETAILER], row[COL_RETAILER_COUNTRY])
        if key in retailer_map:
            continue

        res = conn.execute(
            text("""
            INSERT INTO pricing.retailers (nombre, pais)
            VALUES (:nombre, :pais)
            RETURNING retailer_id
            """),
            {"nombre": key[0], "pais": key[1]},
        )
        new_id = res.scalar()
        retailer_map[key] = new_id
        inserted += 1

    print(f"Retailers nuevos insertados: {inserted}")
    return retailer_map


def load_categories(df, conn):
    """
    Inserta categorías únicas y devuelve
    (nombre_raw, nombre_canonico) -> categoria_id
    """
    print("\n=== Cargando categorías ===")
    cols = [COL_CATEGORY_RAW, COL_CATEGORY_CANON]
    if COL_CATEGORY_IS_IMPUTED in df.columns:
        cols.append(COL_CATEGORY_IS_IMPUTED)

    sub = df[cols].drop_duplicates()

    existing = conn.execute(text("""
        SELECT categoria_id, nombre_raw, nombre_canonico
        FROM pricing.categories
    """)).fetchall()
    cat_map = {(row.nombre_raw, row.nombre_canonico): row.categoria_id for row in existing}

    inserted = 0
    for _, row in sub.iterrows():
        key = (row[COL_CATEGORY_RAW], row[COL_CATEGORY_CANON])
        if key in cat_map:
            continue

        is_imputed = False
        if COL_CATEGORY_IS_IMPUTED in df.columns:
            is_imputed = bool(row.get(COL_CATEGORY_IS_IMPUTED, False))

        res = conn.execute(
            text("""
            INSERT INTO pricing.categories (nombre_raw, nombre_canonico, is_imputed)
            VALUES (:raw, :canon, :is_imp)
            RETURNING categoria_id
            """),
            {"raw": key[0], "canon": key[1], "is_imp": is_imputed},
        )
        new_id = res.scalar()
        cat_map[key] = new_id
        inserted += 1

    print(f"Categorías nuevas insertadas: {inserted}")
    return cat_map


def load_products(df, conn, retailer_map, cat_map):
    """
    Inserta productos y devuelve un mapa
    (retailer_nombre, product_name, unit, brand) -> producto_id
    """
    print("\n=== Cargando productos ===")

    # Definimos clave lógica de producto
    keys = [
        COL_RETAILER,
        COL_PRODUCT_NAME,
        COL_UNIT,
        COL_BRAND,
        COL_PRODUCT_COUNTRY,
        COL_CATEGORY_RAW,
        COL_CATEGORY_CANON,
    ]
    sub = df[keys].drop_duplicates()

    # Leer productos existentes
    existing = conn.execute(text("""
        SELECT p.producto_id,
               r.nombre AS retailer,
               p.nombre_producto,
               p.unidad,
               p.marca,
               p.pais
        FROM pricing.products p
        JOIN pricing.retailers r ON p.retailer_id = r.retailer_id
    """)).fetchall()

    prod_map = {
        (row.retailer, row.nombre_producto, row.unidad, row.marca, row.pais): row.producto_id
        for row in existing
    }

    inserted = 0
    for _, row in sub.iterrows():
        retailer_name = row[COL_RETAILER]
        retailer_country = row[COL_RETAILER_COUNTRY]
        cat_key = (row[COL_CATEGORY_RAW], row[COL_CATEGORY_CANON])

        retailer_id = retailer_map[(retailer_name, retailer_country)]
        categoria_id = cat_map[cat_key]

        key = (
            retailer_name,
            row[COL_PRODUCT_NAME],
            row[COL_UNIT],
            row[COL_BRAND],
            row[COL_PRODUCT_COUNTRY],
        )
        if key in prod_map:
            continue

        res = conn.execute(
            text("""
            INSERT INTO pricing.products (
                retailer_id, categoria_id,
                nombre_producto, marca, unidad, pais
            )
            VALUES (:retailer_id, :categoria_id,
                    :nombre_producto, :marca, :unidad, :pais)
            RETURNING producto_id
            """),
            {
                "retailer_id": retailer_id,
                "categoria_id": categoria_id,
                "nombre_producto": row[COL_PRODUCT_NAME],
                "marca": row[COL_BRAND],
                "unidad": row[COL_UNIT],
                "pais": row[COL_PRODUCT_COUNTRY],
            },
        )
        new_id = res.scalar()
        prod_map[key] = new_id
        inserted += 1

    print(f"Productos nuevos insertados: {inserted}")
    return prod_map


def load_prices(df, conn, prod_map):
    """
    Inserta/actualiza precios (1 registro por producto).
    """
    print("\n=== Cargando precios ===")

    inserted = 0
    updated = 0

    for _, row in df.iterrows():
        key = (
            row[COL_RETAILER],
            row[COL_PRODUCT_NAME],
            row[COL_UNIT],
            row[COL_BRAND],
            row[COL_PRODUCT_COUNTRY],
        )
        producto_id = prod_map.get(key)
        if producto_id is None:
            # algo no se cargó bien en products
            continue

        moneda_local = row.get(COL_CURRENCY)
        precio_local = row.get(COL_PRICE_LOCAL)
        precio_usd = row.get(COL_PRICE_USD)
        fx = row.get(COL_FX)

        is_imp = False
        if COL_PRICE_IS_IMPUTED in df.columns:
            is_imp = bool(row.get(COL_PRICE_IS_IMPUTED, False))

        decision = row.get(COL_PRICE_DECISION)
        razon = row.get(COL_PRICE_REASON)

        # Usamos UPSERT: si ya hay price para ese producto, lo actualizamos
        res = conn.execute(
            text("""
            INSERT INTO pricing.prices (
                producto_id, moneda_local, precio_local,
                precio_usd, fx_local_per_usd,
                is_imputed, decision, razon
            )
            VALUES (
                :producto_id, :moneda_local, :precio_local,
                :precio_usd, :fx, :is_imp, :decision, :razon
            )
            ON CONFLICT (producto_id) DO UPDATE SET
                moneda_local = EXCLUDED.moneda_local,
                precio_local = EXCLUDED.precio_local,
                precio_usd   = EXCLUDED.precio_usd,
                fx_local_per_usd = EXCLUDED.fx_local_per_usd,
                is_imputed   = EXCLUDED.is_imputed,
                decision     = EXCLUDED.decision,
                razon        = EXCLUDED.razon
            """),
            {
                "producto_id": producto_id,
                "moneda_local": moneda_local,
                "precio_local": precio_local,
                "precio_usd": precio_usd,
                "fx": fx,
                "is_imp": is_imp,
                "decision": decision,
                "razon": razon,
            },
        )
        # rowcount no sirve bien con ON CONFLICT; asumimos:
        inserted += 1

    print(f"Precios procesados (insert/upsért): {inserted}")


# ---------------------------------------------------------------------
# 4. MAIN
# ---------------------------------------------------------------------
def main():
    df = get_dataframe()

    with engine.begin() as conn:
        # para no escribir siempre pricing.
        conn.execute(text("SET search_path TO pricing, public"))

        retailer_map = load_retailers(df, conn)
        cat_map = load_categories(df, conn)
        prod_map = load_products(df, conn, retailer_map, cat_map)
        load_prices(df, conn, prod_map)

    print("\n✔ Carga completa.")


if __name__ == "__main__":
    main()
