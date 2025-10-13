import os
import time
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def scraping_guardar_dinamico_txt():
    base_path = Path(__file__).resolve().parent  # Directorio donde está este script

    # Rutas absolutas basadas en la carpeta del script
    urls_path = base_path / "dataset" / "urls_dinamicas.txt"
    excel_path = base_path / "edaSisPricingInt_variables.xlsx"
    output_dir = base_path / "dataset" / "paginas"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verificar si existe el archivo de URLs
    if not urls_path.exists():
        print(f"❌ El archivo de URLs dinámicas no existe: {urls_path}")
        return

    # Leer URLs dinámicas
    with open(urls_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Leer Excel y crear el diccionario
    df = pd.read_excel(excel_path)
    dinamicas = df[df['Formato'] == 'D'][['Pais', 'Variables', 'Link']].dropna()
    url_a_nombre = {
        row['Link']: (
            row['Pais'].strip().lower().replace(" ", "_"),
            row['Variables'].strip().lower().replace(" ", "_")
        )
        for _, row in dinamicas.iterrows()
    }

    # Configuración del navegador
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    driver = webdriver.Chrome(options=chrome_options)

    for url in urls:
        nombre_archivo = "sin_nombre"
        if url in url_a_nombre:
            pais, variable = url_a_nombre[url]
            nombre_archivo = f"{pais}_{variable}.html"
        else:
            nombre_archivo = url.replace("https://", "").replace("/", "_")[:50] + ".html"

        try:
            driver.get(url)
            time.sleep(5)  # espera para cargar contenido
            html = driver.page_source

            with open(output_dir / nombre_archivo, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✅ Guardado: {nombre_archivo}")
        except Exception as e:
            print(f"❌ Error con {url}: {e}")

    driver.quit()

# Ejecutar
if __name__ == "__main__":
    scraping_guardar_dinamico_txt()
