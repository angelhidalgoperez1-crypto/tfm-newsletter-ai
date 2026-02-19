from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

class BaseScraper:
    def __init__(self, source_name, base_domains=None, headers=None):
        self.source_name = source_name
        self.base_domains = base_domains or []
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }

    def get_soup(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 410:
                return None  # fin natural de paginación

            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.HTTPError as e:
            logging.warning(f"[{self.source_name}] HTTP error en {url}: {e}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"[{self.source_name}] Request error en {url}: {e}")

        return None

    def clean_text(self, elements):
        return " ".join(
            [el.get_text(" ", strip=True) for el in elements]
        )

    def build_article(self, url, title, content):
        return {
            "source": self.source_name,
            "url": url,
            "title": title,
            "content": content,
            "scraping_date": datetime.now()
        }

    def can_handle(self, url: str) -> bool:
        """
        Decide si este scraper puede manejar la URL.
        Por defecto, compara el dominio de la URL con base_domains.
        """
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            for d in self.base_domains:
                if d.lower() in netloc:
                    return True
            return False
        except Exception:
            return False