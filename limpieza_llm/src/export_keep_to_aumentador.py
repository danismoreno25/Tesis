import pandas as pd
from pathlib import Path

input_csv = Path("../../extraccion/dataset/llm_cleaned_decisions.csv")
output_csv = Path("../../extraccion/dataset/aumentador_ready.csv")

# Leer resultados del pipeline
df = pd.read_csv(input_csv)

# Filtrar solo los productos válidos
df_keep = df[df["decision"] == "keep"].copy()

# Renombrar columnas al formato del Aumentador
df_keep = df_keep.rename(columns={
    "title": "product_name",
    "category_canonical": "category",
    "price_raw": "price"
})

# Seleccionar solo lo útil
cols = ["product_name", "category", "price", "seller", "country"]
df_keep = df_keep[cols]

# Guardar
df_keep.to_csv(output_csv, index=False)
print(f"[OK] Exportado {len(df_keep)} productos válidos a {output_csv}")


