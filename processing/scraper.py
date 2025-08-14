import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_and_clean_url(url: str) -> str | None:
    """
    Realiza scraping de una URL, limpia el HTML de etiquetas irrelevantes y
    extrae el texto principal.

    Args:
        url (str): La URL de la documentación a procesar.

    Returns:
        str | None: El texto limpio y procesado, o None si ocurre un error.
    """
    try:
        # 1. Realizar la petición HTTP con un User-Agent para simular un navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        # Lanza una excepción si la respuesta no fue exitosa (ej. 404, 500)
        response.raise_for_status()

        # 2. Parsear el contenido HTML con BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # 3. Limpiar el HTML eliminando etiquetas no deseadas
        # Esta lista puede extenderse dependiendo de la estructura de las webs
        tags_to_remove = ['nav', 'footer', 'header', 'aside', 'script', 'style', 'form', 'button']
        for tag in soup.find_all(tags_to_remove):
            tag.decompose()

        # 4. Extraer el texto del cuerpo principal (o del tag principal si se identifica)
        # Intentamos buscar un tag 'main' o 'article', si no, usamos el body
        main_content = soup.find('main') or soup.find('article') or soup.body
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # 5. Normalizar espacios en blanco y saltos de línea
        lines = (line.strip() for line in text.splitlines())
        clean_text = '\n'.join(line for line in lines if line)
        
        logger.info(f"Scraping y limpieza de {url} completado. Caracteres extraídos: {len(clean_text)}")
        return clean_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al intentar acceder a la URL {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado durante el scraping de {url}: {e}")
        return None