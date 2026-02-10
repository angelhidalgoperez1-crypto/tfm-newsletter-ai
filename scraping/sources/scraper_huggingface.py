from scraping.scraper_base import BaseScraper
from datetime import datetime
import time
import logging

class HuggingFaceScraper(BaseScraper):
    def __init__(self, max_pages=50, sleep_time=1.0, exclude_community=True):
        super().__init__("Hugging Face Blog")
        self.base_url = "https://huggingface.co/blog"
        self.max_pages = max_pages
        self.sleep_time = sleep_time
        self.exclude_community = exclude_community

    def get_article_links(self):
        """Extrae enlaces de artículos del blog principal."""
        links = set()
        current_page = 1
        
        while current_page <= self.max_pages:
            # Construir URL con paginación
            url = f"{self.base_url}?p={current_page}" if current_page > 1 else self.base_url
            logging.info(f"Scraping página {current_page}: {url}")
            
            soup = self.get_soup(url)
            if soup is None:
                break

            # Método 1: Buscar artículos por estructura común
            articles_found = False
            
            # Intentar diferentes selectores para encontrar artículos
            article_selectors = [
                'a[href^="/blog/"]',  # Enlaces a artículos del blog
                'article a[href^="/blog/"]',  # Enlaces dentro de elementos article
                'div[class*="article"] a[href^="/blog/"]',  # Enlaces en divs de artículo
            ]
            
            for selector in article_selectors:
                article_links = soup.select(selector)
                if article_links:
                    articles_found = True
                    
                    for link in article_links:
                        href = link['href']
                        
                        # Filtrar solo enlaces a artículos (no a categorías ni otras páginas)
                        if (href.startswith("/blog/") and 
                            not href.startswith("/blog/community") and
                            len(href.split('/')) >= 3 and  # Asegurar que tiene slug: /blog/slug
                            not any(x in href for x in ['?', '#', 'tag=', 'category='])):
                            
                            full_url = f"https://huggingface.co{href}"
                            
                            # Verificar que no sea una URL duplicada (sin parámetros)
                            clean_url = full_url.split('?')[0].split('#')[0]
                            
                            # Si queremos excluir community, verificamos
                            if self.exclude_community:
                                if not self._is_community_url(clean_url):
                                    links.add(clean_url)
                            else:
                                links.add(clean_url)
                    
                    break  # Salir del bucle si encontramos con este selector
            
            # Método 2: Si no encontramos con selectores CSS, buscar por texto
            if not articles_found:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    if href.startswith("/blog/") and not href.startswith("/blog/community"):
                        # Filtrar enlaces que parecen ser artículos
                        link_text = link.get_text(strip=True)
                        if (len(link_text) > 10 and  # No enlaces muy cortos
                            len(href.split('/')) >= 3 and
                            not any(x in href for x in ['?p=', 'tag=', 'category='])):
                            
                            full_url = f"https://huggingface.co{href}"
                            clean_url = full_url.split('?')[0].split('#')[0]
                            
                            if self.exclude_community:
                                if not self._is_community_url(clean_url):
                                    links.add(clean_url)
                            else:
                                links.add(clean_url)

            # Verificar si hay más páginas
            next_button = soup.find('a', string=lambda x: x and 'Next' in x)
            pagination_links = soup.find_all('a', href=lambda x: x and '?p=' in x)
            
            # Buscar el número de página más alto en los enlaces de paginación
            max_page_found = current_page
            for link in pagination_links:
                href = link.get('href', '')
                if '?p=' in href:
                    try:
                        page_num = int(href.split('?p=')[1])
                        if page_num > max_page_found:
                            max_page_found = page_num
                    except:
                        pass
            
            # Si encontramos un botón "Next" o páginas más altas, continuamos
            if next_button or any(link.get_text(strip=True).isdigit() and 
                                int(link.get_text(strip=True)) > current_page 
                                for link in pagination_links):
                current_page += 1
                logging.info(f"Avanzando a página {current_page}. Enlaces encontrados hasta ahora: {len(links)}")
            else:
                logging.info(f"No hay más páginas. Total de enlaces encontrados: {len(links)}")
                break
            
            time.sleep(self.sleep_time)
        
        # Filtrar URLs duplicadas y ordenar
        unique_links = list(links)
        logging.info(f"Total de enlaces únicos encontrados: {len(unique_links)}")
        
        # Mostrar algunos ejemplos
        if unique_links:
            logging.info(f"Primeros 5 enlaces: {unique_links[:5]}")
        
        return unique_links

    def _is_community_url(self, url):
        """Verificación simple si es URL de community."""
        # Puedes implementar una verificación más compleja aquí
        # Por ahora, solo verificamos por patrones comunes
        community_patterns = [
            '/blog/community/',
            '/blog?source=community',
            '/blog?type=community'
        ]
        return any(pattern in url for pattern in community_patterns)

    def scrape_article(self, url):
        """Scrapea un artículo individual."""
        soup = self.get_soup(url)
        if soup is None:
            return None

        # Extraer título
        title_elem = soup.find("h1")
        if not title_elem:
            title_elem = soup.find("title")
        
        title = title_elem.get_text(strip=True) if title_elem else "No title found"
        
        # Limpiar título (remover " - Hugging Face" o similar)
        title = title.split(' - Hugging Face')[0].split(' | Hugging Face')[0]

        # Extraer contenido - múltiples estrategias
        content_div = None
        content_selectors = [
            {"class": "prose"},
            {"class": "markdown"},
            {"class": "content"},
            {"class": "article-content"},
            {"id": "content"},
            {"role": "main"}
        ]
        
        for selector in content_selectors:
            content_div = soup.find("div", selector)
            if content_div:
                break
        
        # Si no encontramos, usar el article o body
        if not content_div:
            content_div = soup.find("article") or soup.find("main") or soup.find("body")
        
        if not content_div:
            logging.warning(f"No se pudo encontrar contenido en {url}")
            return None

        # Extraer párrafos
        paragraphs = content_div.find_all("p")
        content = self.clean_text(paragraphs)
        
        # Si el contenido es muy corto, intentar con todos los textos
        if len(content) < 200:
            all_text = content_div.get_text(" ", strip=True)
            if len(all_text) > len(content):
                content = all_text

        return self.build_article(
            url=url,
            title=title,
            content=content
        )