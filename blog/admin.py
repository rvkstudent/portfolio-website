from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Post, Tag
from markdownx.admin import MarkdownxModelAdmin

class TagAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_en', 'slug')
    prepopulated_fields = {'slug': ('name_ru',)}
    search_fields = ('name_ru', 'name_en')
    
    fieldsets = (
        (None, {
            'fields': ('name_ru', 'name_en', 'slug')
        }),
    )

class PostAdmin(MarkdownxModelAdmin):
    list_display = ('title', 'language', 'get_translation_link', 'created_date', 
                   'published_date', 'get_image_warnings', 'slug')
    list_editable = ('slug',)
    list_filter = ('language', 'created_date', 'published_date', 'tags')
    search_fields = ('title', 'content', 'description')
    filter_horizontal = ('tags',)
    readonly_fields = ('get_translation_link',)
    
    fieldsets = (
        (_('Язык и связь'), {
            'fields': ('language', 'get_translation_link', 'translation_pair')
        }),
        (_('Контент'), {
            'fields': ('title', 'slug', 'description', 'content')
        }),
        (_('Метаданные'), {
            'fields': ('image', 'tags', 'published_date')
        }),
    )
    
    class Media:
        css = {
            'all': ('css/markdown_styles.css',)
        }
        js = ('js/markdown_image_upload.js', 'admin/js/urlify.js')

    # Переименованные методы с get_ префиксом
    def get_translation_link(self, obj):
        if obj.translation_pair:
            url = obj.translation_pair.get_admin_url()
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.translation_pair.title
            )
        return "-"
    get_translation_link.short_description = _('Связанный перевод')
    
    def get_image_warnings(self, obj):
        """Проверяет наличие проблем с изображениями в посте"""
        import re
        from django.conf import settings
        import os
        
        image_pattern = r'!\[.*?\]\(/media/(markdownx/)?([^)]+)\)'
        matches = re.findall(image_pattern, obj.content)
        
        if not matches:
            return format_html('<span class="text-success">✓</span>')
            
        problem_count = 0
        
        for _, filename in matches:
            full_path = os.path.join(settings.MEDIA_ROOT, filename)
            if not os.path.exists(full_path):
                problem_count += 1
        
        if problem_count > 0:
            return format_html(
                '<span class="text-danger">{}⚠</span>', 
                problem_count
            )
        return format_html('<span class="text-success">✓</span>')
    get_image_warnings.short_description = _('Изображения')
    
    def save_model(self, request, obj, form, change):
        if not obj.slug:
            from django.utils.text import slugify
            obj.slug = slugify(obj.title)
            
        from django.core.exceptions import ValidationError
        if Post.objects.filter(slug=obj.slug, language=obj.language).exclude(pk=obj.pk).exists():
            raise ValidationError(f"Пост с таким URL-идентификатором уже существует для языка {obj.get_language_display()}")
            
        if not obj.translation_pair and obj.slug:
            other_lang = 'en' if obj.language == 'ru' else 'ru'
            try:
                pair = Post.objects.get(slug=obj.slug, language=other_lang)
                obj.translation_pair = pair
                pair.translation_pair = obj
                pair.save()
            except Post.DoesNotExist:
                pass
                
        super().save_model(request, obj, form, change)

    # Остальные методы (translation_link, display_tags, image_warnings) остаются без изменений
# Добавляем метод get_admin_url в модель Post
def get_admin_url(self):
    from django.urls import reverse
    return reverse('admin:blog_post_change', args=[self.id])

Post.add_to_class('get_admin_url', get_admin_url)

admin.site.register(Tag, TagAdmin)
admin.site.register(Post, PostAdmin)