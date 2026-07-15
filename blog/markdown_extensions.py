import re
import markdown
from django.conf import settings
from django.utils.safestring import mark_safe
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension

class ImagePathPreprocessor(Preprocessor):
    def run(self, lines):
        new_lines = []
        for line in lines:
            # Ищем шаблон вида ![alt](upload/filename.jpg)
            pattern = r'!\[(.*?)\]\(upload/(.*?)\)'
            # Заменяем на полный путь к медиа
            replacement = r'![\1](' + settings.MEDIA_URL + r'uploads/\2)'
            new_lines.append(re.sub(pattern, replacement, line))
        return new_lines

class ImagePathExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(ImagePathPreprocessor(md), 'image_path_preprocessor', 175)

def convert_markdown(text):
    """Преобразует текст с Markdown в HTML с поддержкой локальных изображений"""
    return mark_safe(markdown.markdown(
        text,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.nl2br',
            'markdown.extensions.tables',
            ImagePathExtension()
        ]
    ))