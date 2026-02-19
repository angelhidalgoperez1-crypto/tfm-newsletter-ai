from scraping.scraper_base import BaseScraper
import logging

class TechCrunchScraper(BaseScraper):

    def __init__(self, tags=None, max_pages=20):
        super().__init__("TechCrunch", base_domains=["techcrunch.com"])

        self.tags = tags or [
            "artificial-intelligence",
            "cloud-computing",
            "robotics"
        ]

        self.base_url = "https://techcrunch.com/tag"
        self.max_pages = max_pages

    def get_article_links(self):
        links = []

        for tag in self.tags:
            for page in range(1, self.max_pages + 1):

                if page == 1:
                    url = f"{self.base_url}/{tag}/"
                else:
                    url = f"{self.base_url}/{tag}/page/{page}/"

                soup = self.get_soup(url)
                if soup is None:
                    break

                articles = soup.select("a.loop-card__title-link")

                if not articles:
                    logging.info(f"[TechCrunch] No más artículos en {tag}, page {page}")
                    break

                for a in articles:
                    href = a.get("href")
                    if href and href.startswith("https://techcrunch.com/"):
                        links.append(href)

        return list(dict.fromkeys(links))

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