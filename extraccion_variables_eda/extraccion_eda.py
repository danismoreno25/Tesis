import pandas as pd
from pathlib import Path

def extraccion_eda():
    # Estás ya en Tesis-Scraping
    base_dir = Path("extraccion_variables_eda")
    file_name = "edaSisPricingInt_variables.xlsx"
    file_path = base_dir / file_name

    # Usar carpeta existente 'dataset'
    output_dir = base_dir / "dataset"

    if not file_path.exists():
        print(f"❌ El archivo no existe: {file_path.resolve()}")
        return

    if not output_dir.exists():
        print(f"❌ La carpeta 'dataset' no existe: {output_dir.resolve()}")
        return

    # Leer archivo Excel
    df = pd.read_excel(file_path)
    print("📄 Archivo leído correctamente")

    if 'Link' not in df.columns or 'Formato' not in df.columns:
        print("❌ Faltan columnas necesarias ('Link', 'Formato')")
        return

    urls_estaticas = df[df['Formato'] == 'E']['Link'].dropna()
    urls_dinamicas = df[df['Formato'] == 'D']['Link'].dropna()

    # Guardar en archivos de texto dentro de dataset
    with open(output_dir / "urls_estaticas.txt", "w", encoding="utf-8") as f_est:
        f_est.write("\n".join(urls_estaticas))

    with open(output_dir / "urls_dinamicas.txt", "w", encoding="utf-8") as f_dyn:
        f_dyn.write("\n".join(urls_dinamicas))

    print("✅ Archivos guardados en 'extraccion_variables_eda/dataset/'")

if __name__ == "__main__":
    extraccion_eda()
