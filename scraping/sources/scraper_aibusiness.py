import time
from scraping.scraper_base import BaseScraper


class AIBusinessScraper(BaseScraper):

    def __init__(self, max_pages=20, sleep_time=1.0):
        super().__init__("AI Business")
        self.base_url = "https://aibusiness.com"
        self.max_pages = max_pages
        self.sleep_time = sleep_time

    def get_article_links(self):
        links = set()

        for page in range(1, self.max_pages + 1):
            url = self.base_url if page == 1 else f"{self.base_url}/page/{page}/"
            soup = self.get_soup(url)

            if soup is None:
                break

            cards = soup.select("h3.listing-title a")
            if not cards:
                break  # no más páginas

            for a in cards:
                href = a.get("href")
                if href and href.startswith("/"):
                    links.add(f"{self.base_url}{href}")

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
