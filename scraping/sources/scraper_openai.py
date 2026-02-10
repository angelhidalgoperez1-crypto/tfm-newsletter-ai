from scraping.scraper_base import BaseScraper

class OpenAIScraper(BaseScraper):

    def __init__(self):
        super().__init__("OpenAI Blog")
        self.base_url = "https://openai.com/es-ES/news/"

    def get_article_links(self):
        soup = self.get_soup(self.base_url)
        if soup is None:
            return []
        
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/es-ES/news/") and href.count("/") > 3:
                links.append("https://openai.com" + href)

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
