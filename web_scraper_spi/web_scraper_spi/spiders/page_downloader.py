import scrapy, os, random, time
from scrapy.http import Request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup


class PageDownloaderSpider(scrapy.Spider):
    name = "page_downloader"

    def __init__(self, urls_file=None, output_dir=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Construir rutas base
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        datos_dir = os.path.join(base_dir, "extraccion", "dataset", "datos_extraidos")

        # Intentar con dinamico.txt primero, si no existe, usar estatico.txt
        default_file = os.path.join(datos_dir, "dinamico.txt")
        if not os.path.exists(default_file):
            default_file = os.path.join(datos_dir, "estatico.txt")

        self.urls_file = urls_file or default_file

        self.output_dir = output_dir or os.path.join(
            base_dir, "extraccion", "dataset", "paginas_descargadas"
        )

        os.makedirs(self.output_dir, exist_ok=True)
        self.counter = 1

    def start_requests(self):
        if not os.path.exists(self.urls_file):
            self.logger.error(f"¡Archivo no encontrado! Verifica la ruta: {self.urls_file}")
            return

        with open(self.urls_file, "r") as f:
            urls = [u.strip() for u in f if u.strip()]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }

        for url in urls:
            yield Request(
                url,
                headers=headers,
                callback=self.save_page,
                errback=self.fallback_with_selenium,
                dont_filter=True
            )

    def save_page(self, response):
        if response.status != 200:
            return self.fallback_with_selenium(response)

        if any(x in response.text.lower() for x in ["mantén presionado el botón", "verifica tu identidad", "captcha"]):
            return self.fallback_with_selenium(response)

        self._guardar_html(response.body)

    def fallback_with_selenium(self, failure):
        url = getattr(getattr(failure, "request", None), "url", None) or \
              getattr(getattr(failure, "value", None), "response", None and {}).url
        if not url:
            self.logger.error("No se pudo obtener la URL del fallback.")
            return

        try:
            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

            driver = webdriver.Chrome(options=opts)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })

            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(2, 4))

            if "px-captcha" in driver.page_source:
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "px-captcha")))
                    button = driver.find_element(By.XPATH,
                                                 "//div[@id='px-captcha']//div[contains(@class,'captcha-button')]")
                    ActionChains(driver).click_and_hold(button).pause(5).release().perform()
                    time.sleep(5)
                except Exception as e:
                    self.logger.warning(f"No se pudo resolver captcha: {e}")

            self._guardar_html(driver.page_source.encode("utf-8"))
            driver.quit()

        except WebDriverException as e:
            self.logger.error(f"Selenium falló en {url}: {e}")

    def _guardar_html(self, contenido):
        soup = BeautifulSoup(contenido, "html.parser")
        body = soup.body
        if not body:
            self.logger.warning("No <body> encontrado.")
            return

        filename = f"{self.counter}.html"
        self.counter += 1
        ruta = os.path.join(self.output_dir, filename)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(str(body))
        self.logger.info(f"Guardado: {ruta}")
