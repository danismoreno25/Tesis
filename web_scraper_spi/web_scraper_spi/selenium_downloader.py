import argparse
import time
import random
from pathlib import Path
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ========== CONFIGURACIÓN ROBUSTA DEL DRIVER ==========
def configurar_driver():
    options = Options()
    options.add_argument("--headless=new")              # headless moderno
    options.add_argument("--no-sandbox")                # evita bloqueos en Linux
    options.add_argument("--disable-dev-shm-usage")     # /dev/shm pequeño en contenedores
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=es-ES,es;q=0.9")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    options.page_load_strategy = "eager"                # no espera recursos pesados

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)                    # clave: timeouts cortos
    driver.set_script_timeout(30)

    # Ocultar bandera webdriver
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

# ========== HELPERS PARA CARGA SEGURA Y REINTENTOS ==========
def safe_navigate(driver, url, wait_body_secs=20):
    """Carga la URL. Si hay timeout, detiene la carga y sigue con lo que haya."""
    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except Exception:
            pass

    # intenta detectar <body> pero no falla si no aparece
    try:
        WebDriverWait(driver, wait_body_secs).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        # Páginas anti-bot a veces ocultan el body; seguimos igual
        pass

def restart_driver(driver):
    try:
        driver.quit()
    except Exception:
        pass
    return configurar_driver()

def guardar_body(html, ruta_archivo):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body:
        ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        ruta_archivo.write_text(str(body), encoding="utf-8")
        print(f"✅ Página guardada en: {ruta_archivo}")
    else:
        print(f"⚠️ No se encontró <body> en {ruta_archivo.name}")

def resolver_captcha(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "px-captcha"))
        )
        button = driver.find_element(By.XPATH, '//div[@id="px-captcha"]//div[contains(@class, "captcha-button")]')
        actions = ActionChains(driver)
        actions.click_and_hold(button).pause(5).release().perform()
        print("✅ Captcha: clic prolongado realizado.")
        time.sleep(5)
    except Exception:
        # si no existe ese captcha, seguimos
        pass

# ========== LOOP PRINCIPAL CON REINTENTO POR URL ==========
def descargar_paginas(urls_file, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        urls = [u.strip() for u in Path(urls_file).read_text(encoding="utf-8").splitlines() if u.strip()]
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {urls_file}")
        return

    driver = configurar_driver()

    for i, url in enumerate(urls, start=1):
        print(f"🌐 Visitando: {url}")
        intento = 1
        max_intentos = 2  # 1 intento + 1 reintento

        while intento <= max_intentos:
            try:
                safe_navigate(driver, url, wait_body_secs=20)
                time.sleep(random.uniform(2.0, 4.0))

                # intenta leer el HTML; si cuelga, lanzará excepción
                html = driver.page_source
                lower = html.lower()

                # heurística simple de captcha
                if any(x in lower for x in ["captcha", "mantén presionado el botón", "verifica tu identidad"]):
                    print("⚠️ Posible captcha/anti-bot detectado. Intentando resolver…")
                    resolver_captcha(driver)
                    time.sleep(2.0)
                    html = driver.page_source

                guardar_body(html, output_dir / f"{i}.html")
                break  # éxito → siguiente URL

            except (TimeoutException, WebDriverException) as e:
                print(f"⚠️ Intento {intento}/{max_intentos} falló: {e}")
                # reinicia el driver para evitar estado zombie
                driver = restart_driver(driver)
                intento += 1
                if intento > max_intentos:
                    print(f"❌ URL fallida definitivamente: {url}")

            finally:
                time.sleep(random.uniform(0.8, 1.6))

    try:
        driver.quit()
    except Exception:
        pass

# ========== CLI ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descargar páginas con Selenium (robusto).")
    parser.add_argument("--urls_file", required=True, help="Ruta al archivo .txt con las URLs.")
    parser.add_argument("--output_dir", required=True, help="Carpeta donde se guardarán los HTML.")
    args = parser.parse_args()
    descargar_paginas(args.urls_file, args.output_dir)
