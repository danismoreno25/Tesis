from supabase import create_client
import pandas as pd

# Conexión a Supabase
url = "https://niieoelzfqiabazbenwn.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5paWVvZWx6ZnFpYWJhemJlbnduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI3OTI0OTIsImV4cCI6MjA3ODM2ODQ5Mn0.YayVvNTL6bqkJvLL3gzK-UqSspaUmsmEha6mAO62DMs"

supabase = create_client(url, key)

PAGE_SIZE = 1000
all_rows = []
start = 0

while True:
    end = start + PAGE_SIZE - 1
    resp = (
        supabase
        .table("items_for_model")
        .select("*")
        .range(start, end)
        .execute()
    )

    batch = resp.data
    if not batch:
        break

    all_rows.extend(batch)

    if len(batch) < PAGE_SIZE:
        break

    start += PAGE_SIZE

df = pd.DataFrame(all_rows)

print("Filas totales:", len(df))
print(df.head())

df.to_csv("items_for_model_from_supabase.csv", index=False)
print("Archivo guardado: items_for_model_from_supabase.csv")