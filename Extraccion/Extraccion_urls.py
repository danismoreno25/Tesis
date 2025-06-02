import pandas as pd
import requests
import os

import ssl
import certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())


def extraer_urls_excel(archivo_excel, nombre_columna='URL', nombre_archivo_salida='urls.txt', hoja=0):
    # Definir ruta donde se guardará el archivo
    carpeta_destino = os.path.join('Extraccion', 'Dataset', 'Datos extraidos')
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_archivo_salida = os.path.join(carpeta_destino, nombre_archivo_salida)

    # Leer el Excel
    df = pd.read_excel(archivo_excel, sheet_name=hoja)
    urls = df[nombre_columna].dropna()

    # Escribir URLs en el archivo de salida
    with open(ruta_archivo_salida, 'w', encoding='utf-8') as archivo:
        for url in urls:
            archivo.write(str(url) + '\n')

    print(f"Se han guardado todas las URLs en '{ruta_archivo_salida}'.")

def descargar_con_user_agent(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Referer': 'https://www.google.com/',
        'Origin': 'https://www.google.com'
    }
    try:
        print(f"Reintentando {url} con User-Agent.")
        respuesta = requests.get(url, headers=headers, timeout=10,verify=certifi.where())
        respuesta.raise_for_status()
        return respuesta.text
    except requests.RequestException as e:
        print(f"Error al descargar {url} con User-Agent: {e}")
        return None

def descargar_codigos_fuente(nombre_archivo_urls=os.path.join('Extraccion', 'Dataset', 'Datos extraidos', 'urls.txt'),
                             carpeta_destino=os.path.join('Extraccion', 'Dataset', 'Datos extraidos', 'paginas_descargadas')):
    os.makedirs(carpeta_destino, exist_ok=True)

    with open(nombre_archivo_urls, 'r', encoding='utf-8') as archivo:
        urls = archivo.readlines()

    for i, url in enumerate(urls, start=1):
        url = url.strip()
        if not url:
            continue
        try:
            print(f"Descargando ({i}/{len(urls)}): {url}")
            respuesta = requests.get(url, timeout=10,verify=certifi.where()) 
            respuesta.raise_for_status()
            contenido = respuesta.text

        except requests.exceptions.HTTPError as e:
            if respuesta.status_code != 200:
                contenido = descargar_con_user_agent(url)
                if contenido is None:
                    continue
            else:
                print(f"Error HTTP al descargar {url}: {e}")
                continue
        except requests.RequestException as e:
            print(f"Error general al descargar {url}: {e}")
            continue

        nombre_archivo = os.path.join(carpeta_destino, f'pagina_{i}.txt')
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)

    print(f"\nTodos los códigos fuente se han guardado en '{carpeta_destino}'.")

# Cambiar la ruta del archivo Excel si es necesario
archivo_excel = 'Extraccion\Dataset\edaSisPricingInt.xlsx'

extraer_urls_excel(archivo_excel)
descargar_codigos_fuente()
