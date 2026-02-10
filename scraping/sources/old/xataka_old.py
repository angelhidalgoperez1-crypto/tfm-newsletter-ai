from scraping.scraper_base import BaseScraper

class XatakaScraper(BaseScraper):

    def __init__(self):
        super().__init__("Xataka")
        self.base_url = "https://www.xataka.com/tag/inteligencia-artificial"

    def get_article_links(self):
        soup = self.get_soup(self.base_url)
        articles = soup.find_all("article")

        links = []
        for art in articles:
            a = art.find("a", href=True)
            if a:
                links.append(a["href"])

        return list(set(links))

    def scrape_article(self, url):
        soup = self.get_soup(url)

        title_tag = soup.find("h1")
        paragraphs = soup.find_all("p")

        if not title_tag or not paragraphs:
            return None

        title = title_tag.get_text(strip=True)
        content = self.clean_text(paragraphs)

        return self.build_article(url, title, content)
