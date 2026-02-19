from scraping.scraper_base import BaseScraper
import logging
import time


class AWSScraper(BaseScraper):

    def __init__(
        self,
        blogs=None,
        lang="es",
        max_pages=30,
        sleep_time=1.0
    ):
        super().__init__("AWS Blog", base_domains=["aws.amazon.com"])

        self.blogs = blogs or [
            "machine-learning",
            "infrastructure-and-automation",
            "iot"
        ]

        self.lang = lang
        self.max_pages = max_pages
        self.sleep_time = sleep_time

        self.base_url = f"https://aws.amazon.com/{self.lang}/blogs"

    def get_article_links(self):
        links = set()

        for blog in self.blogs:
            for page in range(1, self.max_pages + 1):

                if page == 1:
                    url = f"{self.base_url}/{blog}/"
                else:
                    url = f"{self.base_url}/{blog}/page/{page}/"

                soup = self.get_soup(url)
                if soup is None:
                    logging.warning(f"[AWS] Fallo en {url}")
                    break

                articles = soup.select("h2 a[href]")
                if not articles:
                    break  # no más páginas

                for a in articles:
                    href = a.get("href")
                    if href and href.startswith("https://aws.amazon.com/"):
                        links.add(href)

                time.sleep(self.sleep_time)

        return list(links)

    def scrape_article(self, url):
        soup = self.get_soup(url)
        if soup is None:
            return None

        title = soup.find("h1")
        paragraphs = soup.find_all("p")

        if not title or not paragraphs:
            return None

        return self.build_article(
            url,
            title.get_text(strip=True),
            self.clean_text(paragraphs)
        )
