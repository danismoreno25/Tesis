import os
import subprocess

def descargar_paginas_estaticas_y_dinamicas():
    base_dir = os.path.join('dataset', 'datos_extraidos')
    archivo_estaticas = os.path.join(base_dir, 'estaticas.txt')
    archivo_dinamicas = os.path.join(base_dir, 'dinamicas.txt')

    # Ruta absoluta a web_scraper_spi (carpeta hermana de extraccion)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    web_scraper_dir = os.path.join(project_root, 'web_scraper_spi')

    # Ejecutar Scrapy con estaticas
    if os.path.exists(archivo_estaticas):
        try:
            print("Ejecutando Scrapy para páginas estáticas...")
            subprocess.run("scrapy crawl page_downloader", cwd=web_scraper_dir, shell=True, check=True)
            print("Scrapy ejecutado correctamente.")
        except Exception as e:
            print(f"Error ejecutando Scrapy: {e}")
    else:
        print("Archivo de páginas estáticas no encontrado.")

    # Ejecutar Selenium con dinamicas
    if os.path.exists(archivo_dinamicas):
        try:
            print("Ejecutando Selenium para páginas dinámicas...")
            subprocess.run("python3 selenium_downloader.py", cwd=web_scraper_dir, shell=True, check=True)
            print("Selenium ejecutado correctamente.")
        except Exception as e:
            print(f"Error ejecutando Selenium: {e}")
    else:
        print("Archivo de páginas dinámicas no encontrado.")

if __name__ == "__main__":
    descargar_paginas_estaticas_y_dinamicas()