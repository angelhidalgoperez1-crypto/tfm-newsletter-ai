import feedparser
from scraping.scraper_base import BaseScraper


class MicrosoftNewsScraper(BaseScraper):

    def __init__(self, max_pages = 30, sleep_time = 1):
        super().__init__("Microsoft News (AI)")
        self.base_url = "https://news.microsoft.com/feed/?categories=ai"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        self.max_pages = max_pages
        self.sleep_time = sleep_time

    def get_article_links(self):
        links = set()

        for page in range(1, self.max_pages + 1):

            if page == 1:
                url = f"{self.base_url}"
            else:
                url = f"{self.base_url}&_paged={page}"

            soup = self.get_soup(url)
            if soup is None:
                break

            results = soup.find_all("div", class_="listingResult")
            if not results:
                break

            for result in results:
                a = result.find("a", href=True)
                if not a:
                    continue

                href = a["href"]
                if href.startswith("https://news.microsoft.com/"):
                    links.add(href)

            time.sleep(self.sleep_time)

        return list(links)

    def scrape_article(self, url):
        soup = self.get_soup(url)
        if soup is None:
            return None

        title = soup.find("h1")
        paragraphs = soup.select("div.entry-content p")

        if not title or not paragraphs:
            return None

        return self.build_article(
            url=url,
            title=title.get_text(strip=True),
            content=self.clean_text(paragraphs)
        )
