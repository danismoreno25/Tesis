-- Crear esquema
CREATE SCHEMA IF NOT EXISTS pricing;

-- RETAILERS
CREATE TABLE IF NOT EXISTS pricing.retailers (
    retailer_id SERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL,
    pais        TEXT,
    pagina_web  TEXT
);

-- CATEGORÍAS
CREATE TABLE IF NOT EXISTS pricing.categories (
    categoria_id      SERIAL PRIMARY KEY,
    nombre_raw        TEXT,          -- como viene del retailer
    nombre_canonico   TEXT,          -- tu categoría limpia
    is_imputed        BOOLEAN DEFAULT FALSE,
    is_active         BOOLEAN DEFAULT TRUE
);

-- PRODUCTOS
CREATE TABLE IF NOT EXISTS pricing.products (
    producto_id    SERIAL PRIMARY KEY,
    retailer_id    INTEGER NOT NULL REFERENCES pricing.retailers(retailer_id),
    categoria_id   INTEGER NOT NULL REFERENCES pricing.categories(categoria_id),
    nombre_producto TEXT NOT NULL,
    marca          TEXT,
    unidad         TEXT,   -- ej. "5 kg", "1 L"
    pais           TEXT    -- país de venta
);

-- PRECIOS (1 a 1 con PRODUCTO)
CREATE TABLE IF NOT EXISTS pricing.prices (
    producto_id        INTEGER PRIMARY KEY REFERENCES pricing.products(producto_id),
    moneda_local       TEXT,
    precio_local       NUMERIC,
    precio_usd         NUMERIC,
    fx_local_per_usd   NUMERIC,
    is_imputed         BOOLEAN DEFAULT FALSE,
    decision           TEXT,  -- keep / drop / revisar
    razon              TEXT   -- texto libre
);
