import pandas as pd

df = pd.read_csv("items_for_model_from_supabase.csv")

print("Columnas:", df.columns.tolist())
print(df.head())

# revisar si existe la columna objetivo
if "precio_usd_final" not in df.columns:
    raise ValueError("No encuentro la columna 'precio_usd_final' en el dataset")

print("Nulos en precio_usd_final:", df["precio_usd_final"].isna().sum())

# nos quedamos solo con filas que tengan precio
df = df[df["precio_usd_final"].notna()].copy()
print("Filas después de quitar nulos en precio:", len(df))
