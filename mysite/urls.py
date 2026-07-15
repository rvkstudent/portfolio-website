from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from blog.views import custom_image_upload, check_image_exists, switch_language, openclaw_publish_post  # Добавляем импорт switch_language
from django.contrib.sitemaps.views import sitemap
from mysite.sitemaps import StaticViewSitemap, ProjectSitemap, PostSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'projects': ProjectSitemap,
    'posts': PostSitemap,  # Добавляем PostSitemap
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('anki/', include('anki.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('markdownx/', include('markdownx.urls')),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('api/openclaw/posts/', openclaw_publish_post, name='openclaw_publish_post'),
    path('custom-upload/', custom_image_upload, name='custom_image_upload'),
    path('check-image-exists/', check_image_exists, name='check_image_exists'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path('', include('portfolio.urls')),
    path('blog/', include('blog.urls')),
    prefix_default_language=True  # Обязательно True для корректной работы
)

urlpatterns += [
    path('switch-language/<str:lang_code>/', switch_language, name='switch_language'),  # Используем импортированную функцию
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)