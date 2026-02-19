from scraping.scraper_base import BaseScraper
import time
import logging
import random

class HuggingFaceScraper(BaseScraper):
    def __init__(self, max_pages=10, sleep_time=2.0):
        super().__init__("Hugging Face Blog", base_domains=["huggingface.co"])
        self.base_url = "https://huggingface.co/blog"
        self.max_pages = max_pages
        self.sleep_time = sleep_time

    def get_article_links(self):
        links = set()
        for page in range(1, self.max_pages + 1):
            url = self.base_url if page == 1 else f"{self.base_url}?p={page}"
            soup = self.get_soup(url)
            if soup is None:
                break

            # Buscar enlaces a artículos (normalmente dentro de article o en h2)
            for link in soup.find_all("a", href=True):
                href = link['href']
                if href.startswith("/blog/") and href != "/blog/" and "/blog/community" not in href:
                    full_url = "https://huggingface.co" + href
                    links.add(full_url)

            time.sleep(self.sleep_time+random.uniform(0, 3))  # Sleep between 2 and 5 seconds

        return list(links)

    def scrape_article(self, url):
        soup = self.get_soup(url)
        if soup is None:
            return None

        title = soup.find("h1")
        content_div = soup.find("div", class_="prose")
        if not content_div:
            content_div = soup.find("div", class_="markdown")
        if not content_div:
            return None

        paragraphs = content_div.find_all("p")
        if not paragraphs:
            return None

        return self.build_article(
            url=url,
            title=title.get_text(strip=True) if title else "Sin título",
            content=self.clean_text(paragraphs)
        )