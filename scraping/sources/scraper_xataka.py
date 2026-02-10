import time
import logging
from scraping.scraper_base import BaseScraper


class XatakaScraper(BaseScraper):

    def __init__(
        self,
        sections=None,
        max_records=300,
        step=20,
        sleep_time=1.0
    ):
        super().__init__("Xataka")

        # sections = [(tipo, nombre)]
        self.sections = sections or [
            ("tag", "big-data"),
            ("tag", "iot"),
            ("tag", "inteligencia-artificial"),
            ("categoria", "inteligencia-artificial"),
            ("categoria", "robotica-e-ia"),
        ]

        self.max_records = max_records
        self.step = step
        self.sleep_time = sleep_time
        self.base_url = "https://www.xataka.com"

    def get_article_links(self):
        links = set()

        for section_type, name in self.sections:
            for offset in range(0, self.max_records + 1, self.step):

                if offset == 0:
                    url = f"{self.base_url}/{section_type}/{name}"
                else:
                    url = f"{self.base_url}/{section_type}/{name}/record/{offset}"

                soup = self.get_soup(url)
                if soup is None:
                    break

                # Mensaje de fin
                if "¡Lo sentimos!" in soup.get_text():
                    break

                articles = soup.find_all("article")
                if not articles:
                    break

                for article in articles:
                    a = article.find("a", href=True)
                    if not a:
                        continue

                    href = a["href"]
                    if href.startswith("https://www.xataka.com/") and "/tag/" not in href:
                        links.add(href)

                time.sleep(self.sleep_time)

        return list(links)

    def scrape_article(self, url):
        soup = self.get_soup(url)
        if soup is None:
            return None

        title = soup.find("h1")
        paragraphs = soup.select("div.article-content p")

        if not title or not paragraphs:
            return None

        return self.build_article(
            url=url,
            title=title.get_text(strip=True),
            content=self.clean_text(paragraphs)
        )
