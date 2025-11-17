import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# conectar a Supabase
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

# Leer vistas:
df_gold = pd.read_sql("SELECT * FROM pricing.items_gold", engine)
df_need = pd.read_sql("SELECT * FROM pricing.items_needing_imputation", engine)

print("\n=== GOLD (datos buenos para entrenar) ===")
print(df_gold.head())

print("\n=== NEED IMPUTATION (datos sucios) ===")
print(df_need.head())
