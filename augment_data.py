import pandas as pd

INPUT_FILE = "items_for_model_final.csv"
OUTPUT_FILE = "items_augmented.csv"

def augment(df):
    augmented_rows = []

    for _, row in df.iterrows():
        base_price = row["precio_usd_model"]

        # Skip nulos
        if pd.isna(base_price) or base_price <= 0:
            continue

        # Variaciones porcentuales
        factors = [0.90, 0.95, 1.05, 1.10]

        for f in factors:
            new_row = row.copy()
            new_row["precio_usd_model"] = round(base_price * f, 4)
            new_row["is_price_imputed_model"] = False
            new_row["example_id"] = None  # se asignará luego
            new_row["synthetic"] = True
            augmented_rows.append(new_row)

    return pd.DataFrame(augmented_rows)

def main():
    df = pd.read_csv(INPUT_FILE)
    print("Cargando", len(df), "filas reales...")

    df_aug = augment(df)
    print("Generadas", len(df_aug), "filas aumentadas")

    # Unimos
    df_all = pd.concat([df, df_aug], ignore_index=True)

    # Nuevo ID único
    df_all = df_all.reset_index(drop=True)
    df_all["example_id"] = df_all.index + 1

    df_all.to_csv(OUTPUT_FILE, index=False)
    print("Archivo final guardado como:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
