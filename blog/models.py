from django.db import models
from django.utils import timezone
from markdownx.models import MarkdownxField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import get_language
from markdownx.utils import markdownify
from django.views.generic import ListView
from django.conf import settings

class Post(models.Model):
    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('en', 'English'),
    ]
    
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='ru',
        verbose_name='Язык'
    )
    
    translation_pair = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='translations',
        verbose_name='Связанный перевод'
    )
    
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(
        max_length=200,
        unique=False,  # Уникальность обеспечивается constraint
        verbose_name='URL-идентификатор',
        help_text='Часть URL-адреса (должен быть уникальным в рамках языка)'
    )
    
    description = models.TextField(
        max_length=500, 
        blank=True, 
        verbose_name='Краткое описание'
    )
    content = MarkdownxField(verbose_name='Содержание')
    created_date = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    published_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата публикации')
    image = models.ImageField(
        upload_to='blog/%Y/%m/%d/',  # Более организованное хранение
        blank=True, 
        null=True,
        verbose_name='Изображение'
    )
    tags = models.ManyToManyField('Tag', blank=True, related_name='posts', verbose_name='Теги')
    thumbnail = ImageSpecField(
        source='image',
        processors=[ResizeToFill(600, 300)],
        format='JPEG',
        options={'quality': 85}
    )

    def clean(self):
        """Проверка уникальности slug в рамках языка"""
        super().clean()
        if Post.objects.filter(
            slug=self.slug,
            language=self.language
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                'slug': f'Пост с таким URL-идентификатором уже существует для языка {self.get_language_display()}'
            })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Проверка уникальности перед сохранением
        self.full_clean()
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Автоматическое связывание переводов только для новых постов
        if is_new and not self.translation_pair and self.slug:
            self._link_translation()

    def _link_translation(self):
        """Приватный метод для связывания переводов"""
        other_lang = 'en' if self.language == 'ru' else 'ru'
        try:
            pair = Post.objects.get(slug=self.slug, language=other_lang)
            if not pair.translation_pair:
                self.translation_pair = pair
                pair.translation_pair = self
                self.save()
                pair.save()
        except Post.DoesNotExist:
            pass

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={
            'lang': self.language,
            'slug': self.slug
        })

    def formatted_markdown(self):
        """Преобразует Markdown в HTML"""
        return markdownify(self.content)    

    def get_available_translations(self):
        """Возвращает словарь с доступными переводами"""
        translations = {}
        if self.translation_pair:
            for lang_code, lang_name in self.LANGUAGE_CHOICES:
                if lang_code != self.language:
                    trans_post = Post.objects.filter(
                        translation_pair=self.translation_pair,
                        language=lang_code
                    ).first()
                    if trans_post:
                        translations[lang_code] = {
                            'url': trans_post.get_absolute_url(),
                            'title': trans_post.title
                        }
        return translations

    def __str__(self):
        return f"{self.title} ({self.get_language_display()})"

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-published_date']  # Сортировка по дате публикации
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'language'],
                name='unique_slug_per_language'
            )
        ]
    
class Tag(models.Model):
        name_ru = models.CharField(max_length=50, verbose_name='Название (рус)')
        name_en = models.CharField(max_length=50, verbose_name='Название (англ)')
        slug = models.SlugField(max_length=100, unique=True, verbose_name='URL-идентификатор')
        
        def save(self, *args, **kwargs):
            if not self.slug:
                self.slug = slugify(self.name_ru)
            super().save(*args, **kwargs)
        
        def get_name(self):
            """Возвращает название на текущем языке"""
            from django.utils.translation import get_language
            return getattr(self, f'name_{get_language()[:2]}', self.name_ru)
        
        def __str__(self):
            return self.get_name()
        
        class Meta:
            verbose_name = 'Тег'
            verbose_name_plural = 'Теги'

class TagPostsView(ListView):
    template_name = 'blog/tag_posts.html'
    context_object_name = 'posts'

    def get_queryset(self):
        return Post.objects.filter(tags__slug=self.kwargs['slug'])