from django import template
from django.template.defaultfilters import stringfilter
import markdown
from django.utils.safestring import mark_safe
import re
import html

register = template.Library()

@register.filter
@stringfilter
def convert_markdown(value):
    """Преобразует Markdown в HTML с усиленной предварительной обработкой."""
    
    # Предпроцессинг для сложных случаев
    # Сначала убедимся, что мы работаем с сырым текстом
    value = html.unescape(value)
    
    # Разделим текст на строки для более точной обработки
    lines = value.split('\n')
    processed_lines = []
    
    for line in lines:
        # Обработка заголовков
        if re.match(r'^#+\s+', line):
            # Определим уровень заголовка по количеству #
            match = re.match(r'^(#+)\s+(.*?)$', line)
            if match:
                level = len(match.group(1))
                heading_text = match.group(2).strip()
                # Создаем HTML заголовок соответствующего уровня
                if level <= 6:  # HTML поддерживает h1-h6
                    processed_lines.append(f'<h{level}>{heading_text}</h{level}>')
                else:
                    processed_lines.append(f'<h6>{heading_text}</h6>')
                continue
        
        # Если строка не была обработана как заголовок, оставим её без изменений
        processed_lines.append(line)
    
    # Соберём строки обратно
    preprocessed_text = '\n'.join(processed_lines)
    
    # Применим стандартный Markdown-процессор
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
    ]
    
    try:
        # Пробуем применить markdown к предобработанному тексту
        html_content = markdown.markdown(preprocessed_text, extensions=extensions)
    except Exception as e:
        # Если что-то пошло не так, примем простую обработку
        print(f"Ошибка Markdown: {e}")
        html_content = preprocessed_text
    
    return mark_safe(html_content)