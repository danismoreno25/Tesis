import pandas as pd
import subprocess
import os

archivo_excel = os.path.join('extraccion', 'dataset', 'edaSisPricingInt.xlsx')

def extraer_urls_excel(archivo_excel, nombre_columna='URL', nombre_archivo_salida='urls.txt', hoja=0):
    carpeta_destino = os.path.join('extraccion', 'dataset', 'datos_extraidos')
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_archivo_salida = os.path.join(carpeta_destino, nombre_archivo_salida)

    ruta_absoluta = os.path.abspath(archivo_excel)
    df = pd.read_excel(ruta_absoluta, sheet_name=hoja)
    urls = df[nombre_columna].dropna()

    with open(ruta_archivo_salida, 'w', encoding='utf-8') as archivo:
        for url in urls:
            archivo.write(str(url) + '\n')

    print(f"URLs guardadas en: {ruta_archivo_salida}")


def descargar_paginas_scrapy_y_selenium():
    try:
        project_dir = os.path.join(os.getcwd(), 'web_scraper_spi')

        command = f"cd {project_dir} && scrapy crawl page_downloader"
        subprocess.run(command, shell=True, check=True)

        print("Descarga completada con Scrapy!")
    except Exception as e:
        print(f"Error al ejecutar Scrapy: {e}")

def extraccion_controller():
    extraer_urls_excel (archivo_excel)
    descargar_paginas_scrapy_y_selenium()