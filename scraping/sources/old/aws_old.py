from scraping.scraper_base import BaseScraper

class AWSScraper(BaseScraper):

    def __init__(self, max_pages=30):
        super().__init__("AWS Blogs")
        self.base_url = "https://aws.amazon.com/es/blogs/"
        self.categories = [
            "machine-learning",
            "infrastructure-and-automation",
            "iot"
        ]
        self.max_pages = max_pages

    def get_article_links(self):
        links = []

        for category in self.categories:
            # Página principal de la categoría
            url = f"{self.base_url}{category}/"
            soup = self.get_soup(url)
            if soup is None:
                continue

            links.extend(self._extract_links_from_soup(soup))

            # Paginación histórica
            for page in range(2, self.max_pages + 1):
                paged_url = f"{url}page/{page}/"
                soup = self.get_soup(paged_url)
                if soup is None:
                    continue

                links.extend(self._extract_links_from_soup(soup))

        return list(set(links))

    def _extract_links_from_soup(self, soup):
        links = []
        for h2 in soup.find_all("h2"):
            a = h2.find("a", href=True)
            if a:
                links.append(a["href"])
        return links
    
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
