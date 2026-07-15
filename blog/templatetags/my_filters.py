from django import template
from urllib.parse import urlparse, urlunparse

register = template.Library()

@register.filter
def remove_lang(url):
    """Удаляет языковой префикс (/en/, /ru/) из URL"""
    parsed = urlparse(url)
    path = parsed.path
    
    # Удаляем языковой префикс, если он есть
    if path.startswith('/en/') or path.startswith('/ru/'):
        path = path[3:]
    
    return urlunparse(parsed._replace(path=path))