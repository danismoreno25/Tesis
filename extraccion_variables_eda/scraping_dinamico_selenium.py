import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def scraping_guardar_dinamico_txt():
    # Ruta al archivo y carpeta de salida
    urls_path = Path("extraccion_variables_eda/dataset/urls_dinamicas.txt")
    excel_path = Path("extraccion_variables_eda/edaSisPricingInt_variables.xlsx")
    output_dir = Path("extraccion_variables_eda/dataset/paginas")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Leer URLs dinámicas
    if not urls_path.exists():
        print("El archivo de URLs dinámicas no existe.")
        return

    with open(urls_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Crear diccionario de {url: (pais, variable)}
    import pandas as pd
    df = pd.read_excel(excel_path)
    dinamicas = df[df['Formato'] == 'D'][['Pais', 'Variables', 'Link']].dropna()
    url_a_nombre = {
        row['Link']: (row['Pais'].strip().lower().replace(" ", "_"),
                       row['Variables'].strip().lower().replace(" ", "_"))
        for _, row in dinamicas.iterrows()
    }

    # Configuración Selenium
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
            time.sleep(5)
            html = driver.page_source

            with open(output_dir / nombre_archivo, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Guardado: {nombre_archivo}")
        except Exception as e:
            print(f"Error con {url}: {e}")

    driver.quit()

# Ejecutar la función
scraping_guardar_dinamico_txt()
