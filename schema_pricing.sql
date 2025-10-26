CREATE SCHEMA IF NOT EXISTS pricing;

CREATE TABLE IF NOT EXISTS pricing.items_raw (
  id BIGSERIAL PRIMARY KEY,
  title TEXT,
  description TEXT,
  breadcrumbs TEXT,
  price_raw TEXT,
  currency_raw TEXT,
  url TEXT,
  seller TEXT,
  availability TEXT,
  country TEXT,
  ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pricing.items_curated (
  id BIGSERIAL PRIMARY KEY,
  title TEXT,
  title_es TEXT,
  description TEXT,
  description_es TEXT,
  breadcrumbs TEXT,
  price_numeric NUMERIC(12,2),
  currency_code TEXT,
  url TEXT,
  seller TEXT,
  availability TEXT,
  country TEXT,
  source_hash TEXT UNIQUE,
  processed_at TIMESTAMP DEFAULT NOW()
);


-- Índices para mejorar búsquedas
CREATE INDEX IF NOT EXISTS idx_curated_price     ON pricing.items_curated (price_numeric);
CREATE INDEX IF NOT EXISTS idx_curated_seller    ON pricing.items_curated (seller);
CREATE INDEX IF NOT EXISTS idx_curated_country   ON pricing.items_curated (country);



