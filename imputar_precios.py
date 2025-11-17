import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

# 1. Leemos las vistas
df_gold = pd.read_sql("SELECT * FROM pricing.items_gold", engine)
df_need = pd.read_sql("SELECT * FROM pricing.items_needing_imputation", engine)

# Nos quedamos solo con filas que tienen precio limpio
df_gold_valid = df_gold[df_gold["precio_usd_clean"].notna()].copy()

# 2. Calculamos medianas por (categoria, país del retailer)
group_cols = ["category_canonical", "retailer_country"]
medianas = (
    df_gold_valid
    .groupby(group_cols)["precio_usd_clean"]
    .median()
    .reset_index()
    .rename(columns={"precio_usd_clean": "precio_median_group"})
)

# Mediana global como último recurso
global_median = df_gold_valid["precio_usd_clean"].median()

print("Mediana global:", global_median)

# 3. Preparamos df_need para imputar
df_need_imp = df_need.copy()

# Hacemos merge para traer la mediana de cada grupo
df_need_imp = df_need_imp.merge(
    medianas,
    on=group_cols,
    how="left"
)

# Columna nueva: precio imputado
df_need_imp["precio_usd_imputed"] = df_need_imp["precio_usd_clean"]

# Mask: dónde hay que imputar (precio_usd_clean es NULL)
mask_null = df_need_imp["precio_usd_imputed"].isna()

# Primero intentamos con la mediana del grupo
df_need_imp.loc[mask_null, "precio_usd_imputed"] = df_need_imp.loc[mask_null, "precio_median_group"]

# Si aún quedan NaN (grupos raros), usamos la mediana global
mask_null2 = df_need_imp["precio_usd_imputed"].isna()
df_need_imp.loc[mask_null2, "precio_usd_imputed"] = global_median

# Marcamos la fuente de imputación
df_need_imp["imputation_source"] = "median_category_country"
df_need_imp.loc[mask_null2, "imputation_source"] = "global_median"

# 4. Guardamos resultados a CSV
df_need_imp.to_csv("items_needing_imputation_imputed.csv", index=False)

print("Guardado items_needing_imputation_imputed.csv con",
      len(df_need_imp), "filas.")

# 5. Construimos dataset final para el modelo

# Para las filas gold, usamos el precio limpio tal cual
df_gold_model = df_gold_valid.copy()
df_gold_model["precio_usd_model"] = df_gold_model["precio_usd_clean"]
df_gold_model["is_price_imputed_model"] = False
df_gold_model["imputation_source"] = "original_clean"

# Para las filas needing_imputation, usamos el precio imputado
df_need_model = df_need_imp.copy()
df_need_model["precio_usd_model"] = df_need_model["precio_usd_imputed"]
df_need_model["is_price_imputed_model"] = True

# Unimos todo
df_model = pd.concat([df_gold_model, df_need_model], ignore_index=True)

df_model.to_csv("items_for_model_final.csv", index=False)
print("Guardado items_for_model_final.csv con", len(df_model), "filas.")
