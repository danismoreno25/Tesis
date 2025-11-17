import pandas as pd
import unidecode

df = pd.read_csv("items_for_model_from_supabase.csv")

# 1. Nombre de columnas uniformes
df.columns = (
    df.columns
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("-", "_")
)

# 2. Normalización de strings generales
def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x)
    x = unidecode.unidecode(x)  # quitar tildes
    x = x.strip().lower()       # minusculas
    x = x.replace("  ", " ")    # dobles espacios
    x = x.replace("\n", " ")    # saltos
    x = x.replace("\t", " ")    # tabs
    return x

for col in ["product_name", "product_country", "imputation_source"]:
    if col in df.columns:
        df[col] = df[col].apply(clean_text)

# 3. Limpiar retailer_id (solo numeros validos)
df = df[df["retailer_id"].notna()]
df = df[df["retailer_id"].astype(str).str.isdigit()]
df["retailer_id"] = df["retailer_id"].astype(int)

# 4. Convertir tipos
df["precio_usd_final"] = pd.to_numeric(df["precio_usd_final"], errors="coerce")
df = df[df["precio_usd_final"].notna()]

# 5. Crear columna limpia de nombres (clave)
df["product_name_clean"] = (
    df["product_name"]
    .str.replace(r"\d+g", "", regex=True)
    .str.replace(r"\d+ml", "", regex=True)
    .str.replace(r"\d+kg", "", regex=True)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# 6. Eliminar duplicados lógicos
df = df.drop_duplicates(
    subset=["product_name_clean", "retailer_id", "product_country"],
    keep="first"
)

# 7. Guardar resultado
df.to_csv("items_clean_deep.csv", index=False)

print("Limpieza profunda terminada. Filas finales:", len(df))
