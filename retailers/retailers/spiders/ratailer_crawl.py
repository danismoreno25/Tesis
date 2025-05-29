import scrapy


class RatailerCrawlSpider(scrapy.Spider):
    name = "ratailer-crawl"
    allowed_domains = ["www.chedraui.com.mx"]
    start_urls = ["https://www.chedraui.com.mx/arroz-schettino-verde-900g-3008386/p"]

    def parse(self, response):
        print(response.url)
        pass
