from scraping.scraper_base import BaseScraper

class TechCrunchScraper(BaseScraper):

    def __init__(self, max_pages=20):
        super().__init__("TechCrunch")
        self.base_url = "https://techcrunch.com/tag/artificial-intelligence/"
        self.max_pages = max_pages

    def get_article_links(self):
        links = []

        for page in range(1, self.max_pages + 1):
            url = f"{self.base_url}page/{page}/"
            soup = self.get_soup(url)
            if soup is None:
                continue

            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("https://techcrunch.com/") and "/202" in href:
                    links.append(href)

        return list(set(links))

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
