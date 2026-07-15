from django.db import models
from ckeditor.fields import RichTextField
from django_ckeditor_5.fields import CKEditor5Field
from django.utils.html import strip_tags
from markdownx.models import MarkdownxField
from bs4 import BeautifulSoup
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from markdownx.utils import markdownify
from django.utils.translation import get_language

def clean_html_content(html_content):
    if not html_content:
        return html_content
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Удаляем все атрибуты style и span с цветом
    for tag in soup.find_all(True):
        if tag.name == 'span' and tag.get('style') and 'color' in tag.get('style'):
            tag.unwrap()
        if 'style' in tag.attrs:
            del tag.attrs['style']
    
    return str(soup)

class Portfolio(models.Model):
    # Персональная информация (из About)
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    position = models.CharField(max_length=200, verbose_name='Должность')
    bio_title = models.CharField(max_length=200, verbose_name='Заголовок биографии')
    bio_content = models.TextField(verbose_name='Содержание биографии')
    photo = models.ImageField(upload_to='about/', blank=True, verbose_name='Фото')
    skills = models.TextField(verbose_name='Навыки и технологии')

    # Контактная информация
    email = models.EmailField(verbose_name='Email')
    github = models.URLField(blank=True, verbose_name='GitHub')
    linkedin = models.URLField(blank=True, verbose_name='LinkedIn')
    telegram = models.CharField(max_length=100, blank=True, verbose_name='Telegram')
    
    # Резюме в PDF
    resume_pdf = models.FileField(
        upload_to='resume/',
        blank=True,
        verbose_name='Резюме (PDF)',
        help_text='Загрузите ваше резюме в формате PDF'
    )

    # Дата последнего обновления
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')

    class Meta:
        verbose_name = 'Портфолио'
        verbose_name_plural = 'Портфолио'

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        self.bio_content = clean_html_content(self.bio_content)
        self.skills = clean_html_content(self.skills)
        super().save(*args, **kwargs)

class Project(models.Model):
    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('en', 'English'),
    ]

    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='ru',
        verbose_name=_('Язык')
    )

    translation_pair = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='translations',
        verbose_name=_('Связанный перевод')
    )

    title_ru = models.CharField(max_length=200, verbose_name=_('Название проекта (RU)'))
    title_en = models.CharField(max_length=200, verbose_name=_('Название проекта (EN)'))
    description_ru = MarkdownxField(verbose_name=_('Описание (RU)'))
    description_en = MarkdownxField(verbose_name=_('Описание (EN)'))
    technology = models.CharField(max_length=200, verbose_name=_('Технологии'))
    image = models.ImageField(
        upload_to='portfolio/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name=_('Изображение')
    )
    slug = models.SlugField(
        max_length=200,
        unique=False,
        verbose_name=_('URL-идентификатор'),
        help_text=_('Часть URL-адреса (должен быть уникальным в рамках языка)')
    )
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    modified_at = models.DateTimeField(auto_now=True)

    def get_absolute_url(self):
        return reverse('portfolio:project_detail', kwargs={
            'lang': self.language,
            'slug': self.slug
        })

    def formatted_markdown(self):
        """Преобразует Markdown в HTML с учётом текущего языка."""
        current_language = get_language()
        if current_language == 'ru':
            return markdownify(self.description_ru)
        else:
            return markdownify(self.description_en)  

    def __str__(self):
        return f"{self.title_ru} / {self.title_en}"

    class Meta:
        verbose_name = _('Проект')
        verbose_name_plural = _('Проекты')
        ordering = ['-created_date']
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'language'],
                name='unique_slug_per_language_project'
            )
        ]

class WorkExperienceItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, related_name='work_experiences', on_delete=models.CASCADE)
    company = models.CharField(max_length=255, verbose_name='Компания')
    position = models.CharField(max_length=255, verbose_name='Должность')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    description = CKEditor5Field(verbose_name='Описание обязанностей', config_name='extends')  # Изменено на CKEditor5Field
    technologies = models.CharField(max_length=500, blank=True, verbose_name='Используемые технологии')
    is_current = models.BooleanField(default=False, verbose_name='Текущее место работы')
    
    class Meta:
        verbose_name = 'Опыт работы'
        verbose_name_plural = 'Опыт работы'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.position} в {self.company}"

    def save(self, *args, **kwargs):
        # Удаляем этот метод, так как CKEditor5Field не требует очистки
        # При использовании CKEditor поле будет автоматически обрабатывать HTML
        super().save(*args, **kwargs)

class EducationItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, related_name='education_items', on_delete=models.CASCADE)
    institution = models.CharField(max_length=255, verbose_name='Учебное заведение')
    degree = models.CharField(max_length=255, verbose_name='Степень/Специальность')
    field_of_study = models.CharField(max_length=255, verbose_name='Направление обучения')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_current = models.BooleanField(default=False, verbose_name='Текущее место учебы')

    class Meta:
        verbose_name = 'Образование'
        verbose_name_plural = 'Образование'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.degree} - {self.institution}"

class CertificateItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, related_name='certificates', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='certificates/', verbose_name='Изображение сертификата')
    file = models.FileField(upload_to='certificates/', verbose_name='Файл сертификата')
    date_received = models.DateField(verbose_name='Дата получения')

    class Meta:
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'
        ordering = ['-date_received']

    def __str__(self):
        return self.title

class YearAchievements(models.Model):
    year = models.IntegerField(unique=True, verbose_name="Год")
    # Заголовок и подзаголовок страницы
    page_title_ru = models.CharField(max_length=300, blank=True, verbose_name="Заголовок страницы (RU)", help_text="Например: Ключевые достижения за 2025 год. Oracle PL/SQL Developer")
    page_title_en = models.CharField(max_length=300, blank=True, verbose_name="Заголовок страницы (EN)", help_text="Например: Key Achievements for 2025. Oracle PL/SQL Developer")
    page_subtitle_ru = models.CharField(max_length=200, blank=True, verbose_name="Подзаголовок/Должность (RU)", help_text="Например: Системный интегратор")
    page_subtitle_en = models.CharField(max_length=200, blank=True, verbose_name="Подзаголовок/Должность (EN)", help_text="Например: System Integrator")
    
    # SEO поля
    meta_title_ru = models.CharField(max_length=70, blank=True, verbose_name="SEO Title (RU)", help_text="Оптимально 50-60 символов. Если пусто, используется page_title")
    meta_title_en = models.CharField(max_length=70, blank=True, verbose_name="SEO Title (EN)", help_text="Оптимально 50-60 символов. Если пусто, используется page_title")
    meta_description_ru = models.CharField(max_length=160, blank=True, verbose_name="SEO Description (RU)", help_text="Оптимально 150-160 символов")
    meta_description_en = models.CharField(max_length=160, blank=True, verbose_name="SEO Description (EN)", help_text="Оптимально 150-160 символов")
    meta_keywords_ru = models.CharField(max_length=255, blank=True, verbose_name="SEO Keywords (RU)", help_text="Ключевые слова через запятую")
    meta_keywords_en = models.CharField(max_length=255, blank=True, verbose_name="SEO Keywords (EN)", help_text="Ключевые слова через запятую")
    og_image = models.ImageField(upload_to='achievements/', blank=True, null=True, verbose_name="Open Graph изображение", help_text="Рекомендуется 1200x630px для социальных сетей")
    
    # Контент секций
    tech_stack_ru = models.TextField(verbose_name="Технологический стек (RU)")
    tech_stack_en = models.TextField(verbose_name="Технологический стек (EN)")
    business_results_ru = models.TextField(verbose_name="Бизнес-результаты (RU)")
    business_results_en = models.TextField(verbose_name="Бизнес-результаты (EN)")
    key_competencies_ru = models.TextField(verbose_name="Ключевые компетенции (RU)")
    key_competencies_en = models.TextField(verbose_name="Ключевые компетенции (EN)")
    summary_ru = models.TextField(verbose_name="Краткое резюме (RU)")
    summary_en = models.TextField(verbose_name="Краткое резюме (EN)")
    # Описание крупных проектов в формате Markdown (для вывода как единый блок)
    projects_ru = models.TextField(blank=True, verbose_name="Описание крупных проектов (RU)")
    projects_en = models.TextField(blank=True, verbose_name="Описание крупных проектов (EN)")
    # Обучение и развитие
    learning_development_ru = models.TextField(blank=True, verbose_name="Обучение и развитие (RU)")
    learning_development_en = models.TextField(blank=True, verbose_name="Обучение и развитие (EN)")
    
    class Meta:
        verbose_name = "Достижения за год"
        verbose_name_plural = "Достижения по годам"
        ordering = ['-year']
    
    def __str__(self):
        return f"Достижения {self.year}"