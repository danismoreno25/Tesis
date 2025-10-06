import os
import subprocess
from pathlib import Path

def descargar_paginas_estaticas_y_dinamicas():
    # Rutas base
    extraccion_dir = os.path.dirname(os.path.abspath(__file__))  # .../extraccion
    base_dir = os.path.join(extraccion_dir, 'dataset', 'datos_extraidos')
    archivo_estaticas = os.path.join(base_dir, 'estaticas.txt')
    archivo_dinamicas = os.path.join(base_dir, 'dinamicas.txt')

    # Ruta absoluta a la carpeta del scraper (hermana de "extraccion")
    project_root = os.path.dirname(extraccion_dir)               # .../Tesis-Scraping
    web_scraper_dir = os.path.join(project_root, 'web_scraper_spi')

    # Localiza selenium_downloader.py en uno de estos posibles lugares
    candidatos = [
        os.path.join(web_scraper_dir, 'selenium_downloader.py'),
        os.path.join(web_scraper_dir, 'web_scraper_spi', 'selenium_downloader.py'),
    ]
    selenium_script = next((p for p in candidatos if os.path.isfile(p)), None)

    # --- SCRAPY (estáticas) ---
    if os.path.exists(archivo_estaticas):
        try:
            print("Ejecutando Scrapy para páginas estáticas...")
            # 'python -m scrapy' es más robusto que 'scrapy ...'
            subprocess.run(
                ["python3", "-m", "scrapy", "crawl", "page_downloader"],
                cwd=web_scraper_dir,
                check=True
            )
            print("Scrapy ejecutado correctamente.")
        except Exception as e:
            print(f"Error ejecutando Scrapy: {e}")
    else:
        print("Archivo de páginas estáticas no encontrado:", archivo_estaticas)

    # --- SELENIUM (dinámicas) ---
    if os.path.exists(archivo_dinamicas):
        try:
            if selenium_script is None:
                raise FileNotFoundError(
                    f"No se encontró selenium_downloader.py en: {candidatos}"
                )

            print("Ejecutando Selenium para páginas dinámicas...")
            ruta_urls = os.path.abspath(archivo_dinamicas)
            salida_paginas = os.path.abspath(os.path.join(extraccion_dir, 'dataset', 'paginas_descargadas'))
            Path(salida_paginas).mkdir(parents=True, exist_ok=True)

            # Llama al script con argumentos requeridos (sin shell)
            subprocess.run(
                ["python3", selenium_script, "--urls_file", ruta_urls, "--output_dir", salida_paginas],
                cwd=web_scraper_dir,
                check=True
            )
            print("Selenium ejecutado correctamente.")
        except Exception as e:
            print(f"Error ejecutando Selenium: {e}")
    else:
        print("Archivo de páginas dinámicas no encontrado:", archivo_dinamicas)
if __name__ == "__main__":
    descargar_paginas_estaticas_y_dinamicas()
    
    