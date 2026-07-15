from django import template
from django.urls import resolve, reverse
from django.utils.translation import activate, get_language

register = template.Library()

@register.simple_tag(takes_context=True)
def translate_url(context, lang_code):
    # Получаем текущий путь и параметры
    current_path = context['request'].path
    
    # Получаем текущий язык
    current_lang = get_language()
    
    # Если путь начинается с языкового префикса, заменяем его
    if current_path.startswith(f'/{current_lang}/'):
        translated_path = current_path.replace(f'/{current_lang}/', f'/{lang_code}/', 1)
    else:
        # Для путей без языкового префикса
        translated_path = f'/{lang_code}{current_path}'
    
    return translated_path