import scrapy
from scrapy.http import Request
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time

from selenium.webdriver.common.action_chains import ActionChains

class PageDownloaderSpider(scrapy.Spider):
    name = 'page_downloader'

    def __init__(self, *args, **kwargs):
        super(PageDownloaderSpider, self).__init__(*args, **kwargs)
        self.counter = 1
        self.project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.urls_file = os.path.join(self.project_dir, 'extraccion', 'dataset', 'datos_extraidos', 'urls.txt')

    def start_requests(self):
        try:
            with open(self.urls_file, 'r') as f:
                urls = f.readlines()

            for url in urls:
                url = url.strip()
                if url:
                    print("Request: " + url)
                    headers = {
                        'User-Agent': (
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                            '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
                        ),
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }

                    yield Request(
                        url,
                        callback=self.save_page,
                        errback=self.fallback_with_selenium,
                        headers=headers,
                        dont_filter=True
                    )
        except FileNotFoundError:
            self.logger.error(f"¡Archivo no encontrado! Verifica la ruta: {self.urls_file}")


    def save_page(self, response):
        if response.status != 200:
            return self.fallback_with_selenium(response)

        body_text = response.text.lower()
        if "mantén presionado el botón" in body_text or "verifica tu identidad" in body_text:
            print("⚠️ Captcha detectado en Scrapy. Usando Selenium como fallback...")
            return self.fallback_with_selenium(response)

        self._guardar_html(response.body)

    def fallback_with_selenium(self, failure):
        if hasattr(failure, 'request'):
            url = failure.request.url
        elif hasattr(failure, 'value') and hasattr(failure.value, 'response'):
            url = failure.value.response.url
        else:
            self.logger.error("Error desconocido en fallback.")
            return

        self.logger.warning(f"Selenium usándose como fallback para: {url}")

        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )
            options.add_argument(f'user-agent={user_agent}')

            driver = webdriver.Chrome(options=options)

            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })

            print(f"Cargando con Selenium: {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception as e:
                print("Timeout esperando el <body>")

            time.sleep(random.uniform(2.0, 4.5))

            if "Mantén presionado el botón" or "Verifica tu identidad" or "Verifica" or "Mantén" in driver.page_source:
                print("⚠️ Captcha detectado. Intentando resolver...")

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "px-captcha"))
                    )

                    button = driver.find_element(By.XPATH, '//div[@id="px-captcha"]//div[contains(@class, "captcha-button")]')

                    actions = ActionChains(driver)
                    actions.click_and_hold(button).pause(5).release().perform()
                    print("✅ Captcha presionado y soltado.")
                    time.sleep(5)

                except Exception as e:
                    print(f"❌ Error interactuando con el captcha: {e}")

            page_source = driver.page_source
            driver.quit()

            self._guardar_html(page_source.encode('utf-8'))

        except WebDriverException as e:
            self.logger.error(f"Selenium falló al descargar {url}: {e}")


    def _guardar_html(self, contenido):
        soup = BeautifulSoup(contenido, 'html.parser')
        body = soup.body

        if body is None:
            self.logger.warning("No se encontró <body> en el HTML.")
            return

        output_dir = os.path.join(self.project_dir, 'extraccion', 'dataset', 'paginas_descargadas')
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{self.counter}.html"
        self.counter += 1
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(body))

        self.logger.info(f"Guardado solo <body>: {filepath}")
