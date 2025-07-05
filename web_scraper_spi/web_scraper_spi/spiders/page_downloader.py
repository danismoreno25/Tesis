import scrapy
import os

class PageDownloaderSpider(scrapy.Spider):
    name = "page_downloader"

    def __init__(self, urls_file=None, output_dir=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls_file = urls_file
        self.output_dir = output_dir

    def start_requests(self):
        if not self.urls_file or not os.path.exists(self.urls_file):
            self.logger.error("El archivo de URLs no fue encontrado.")
            return

        with open(self.urls_file, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]

        for idx, url in enumerate(urls):
            yield scrapy.Request(url=url, callback=self.save_html, meta={'idx': idx})

    def save_html(self, response):
        idx = response.meta['idx']
        filename = os.path.join(self.output_dir, f"pagina_estatica_{idx}.html")
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log(f"Página guardada: {filename}")
