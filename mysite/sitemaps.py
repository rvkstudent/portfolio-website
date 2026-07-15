from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blog.models import Post
from portfolio.models import Project

class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Возвращаем только опубликованные посты
        return Post.objects.filter(published_date__isnull=False)

    def lastmod(self, obj):
        return obj.published_date

    def location(self, obj):
        # Возвращаем полный путь с языковым префиксом
        return f"/{obj.language}/blog/post/{obj.slug}/"

class ProjectLanguageProxy:
    """Вспомогательный класс для создания языковых версий проектов"""
    def __init__(self, project, language):
        self.project = project
        self.language = language
        self.modified_at = project.modified_at
        self.slug = project.slug

class ProjectSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Получаем все активные проекты
        projects = Project.objects.filter(is_active=True)
        
        # Создаем список проектов с учетом языка
        localized_projects = []
        
        for project in projects:
            # Если у проекта есть русское описание/название, добавляем русскую версию
            if project.title_ru and project.description_ru:
                localized_projects.append(ProjectLanguageProxy(project, 'ru'))
            
            # Если у проекта есть английское описание/название, добавляем английскую версию
            if project.title_en and project.description_en:
                localized_projects.append(ProjectLanguageProxy(project, 'en'))
        
        return localized_projects

    def lastmod(self, obj):
        return obj.modified_at

    def location(self, obj):
        # Генерируем URL с учетом языка
        return f"/{obj.language}/projects/{obj.slug}/"

class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        # Указываем только существующие маршруты
        return ['portfolio:home', 'portfolio:about']

    def location(self, item):
        return reverse(item)