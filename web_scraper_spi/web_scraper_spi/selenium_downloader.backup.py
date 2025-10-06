import argparse
import os
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
from selenium.common.exceptions import WebDriverException


def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)

    # Evitar detección como bot
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    return driver


def guardar_body(html, ruta_archivo):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(str(body))
        print(f"✅ Página guardada en: {ruta_archivo}")
    else:
        print(f"⚠️ No se encontró <body> en {ruta_archivo}")


def resolver_captcha(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "px-captcha"))
        )
        button = driver.find_element(By.XPATH, '//div[@id="px-captcha"]//div[contains(@class, "captcha-button")]')

        actions = ActionChains(driver)
        actions.click_and_hold(button).pause(5).release().perform()
        print("✅ Captcha resuelto con clic prolongado.")
        time.sleep(5)
    except Exception as e:
        print(f"❌ Error resolviendo captcha: {e}")


def descargar_paginas(urls_file, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(urls_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {urls_file}")
        return

    driver = configurar_driver()

    for i, url in enumerate(urls, start=1):
        print(f"🌐 Visitando: {url}")
        try:
            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception:
                print("⏱️ Timeout esperando <body>")

            time.sleep(random.uniform(2.0, 4.5))

            # Detección de captcha en el contenido
            page_lower = driver.page_source.lower()
            if "mantén presionado el botón" in page_lower or "verifica tu identidad" in page_lower:
                print("⚠️ Captcha detectado. Intentando resolver...")
                resolver_captcha(driver)

            html = driver.page_source
            filename = f"{i}.html"
            ruta_archivo = output_dir / filename
            guardar_body(html, ruta_archivo)

        except WebDriverException as e:
            print(f"❌ Error al cargar {url}: {e}")

    driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descargar páginas con Selenium.")
    parser.add_argument("--urls_file", required=True, help="Ruta al archivo .txt con las URLs.")
    parser.add_argument("--output_dir", required=True, help="Carpeta donde se guardarán los HTML.")
    args = parser.parse_args()

    descargar_paginas(args.urls_file, args.output_dir)
