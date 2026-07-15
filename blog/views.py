import os
import uuid
import json
import glob
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import get_language
from django.utils.text import slugify
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse  # <-- Добавьте этот импорт
from PIL import Image
from .models import Post, Tag


def _parse_publish_datetime(value):
    if not value:
        return timezone.now()

    if isinstance(value, datetime):
        parsed_value = value
    else:
        try:
            parsed_value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValidationError({'published_date': 'Invalid ISO datetime format'}) from exc

    if timezone.is_naive(parsed_value):
        return timezone.make_aware(parsed_value, timezone.get_current_timezone())
    return parsed_value


def _normalize_tag_payload(tag_payload):
    if isinstance(tag_payload, str):
        label = tag_payload.strip()
        if not label:
            raise ValidationError({'tags': 'Tag values must not be empty'})
        return label, label

    if not isinstance(tag_payload, dict):
        raise ValidationError({'tags': 'Each tag must be either a string or an object'})

    name_ru = (tag_payload.get('name_ru') or '').strip()
    name_en = (tag_payload.get('name_en') or '').strip()
    name = (tag_payload.get('name') or '').strip()

    if not name_ru and not name_en and not name:
        raise ValidationError({'tags': 'Tag object must contain name, name_ru, or name_en'})

    if not name_ru:
        name_ru = name or name_en
    if not name_en:
        name_en = name or name_ru

    return name_ru, name_en


def _resolve_tags(tag_values):
    resolved_tags = []
    for tag_payload in tag_values:
        name_ru, name_en = _normalize_tag_payload(tag_payload)
        tag_slug = slugify(name_en or name_ru)
        if not tag_slug:
            raise ValidationError({'tags': 'Tag slug could not be generated'})

        tag, _ = Tag.objects.get_or_create(
            slug=tag_slug,
            defaults={'name_ru': name_ru, 'name_en': name_en},
        )

        updated_fields = []
        if not tag.name_ru and name_ru:
            tag.name_ru = name_ru
            updated_fields.append('name_ru')
        if not tag.name_en and name_en:
            tag.name_en = name_en
            updated_fields.append('name_en')
        if updated_fields:
            tag.save(update_fields=updated_fields)

        resolved_tags.append(tag)

    return resolved_tags


def _extract_api_token(request):
    authorization_value = request.headers.get('Authorization', '')
    if authorization_value.startswith('Bearer '):
        return authorization_value.split(' ', 1)[1].strip()
    return request.headers.get('X-API-Key', '').strip()


@csrf_exempt
@require_POST
def openclaw_publish_post(request):
    configured_token = getattr(settings, 'OPENCLAW_BLOG_API_TOKEN', '')
    if not configured_token:
        return JsonResponse({'error': 'OpenClaw publishing is not configured'}, status=503)

    provided_token = _extract_api_token(request)
    if provided_token != configured_token:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    title = (payload.get('title') or '').strip()
    content = payload.get('content')
    language = (payload.get('language') or 'ru').strip()
    tag_values = payload.get('tags') or []

    if not title:
        return JsonResponse({'error': 'Field "title" is required'}, status=400)
    if not content:
        return JsonResponse({'error': 'Field "content" is required'}, status=400)
    if language not in dict(Post.LANGUAGE_CHOICES):
        return JsonResponse({'error': 'Unsupported language'}, status=400)
    if not isinstance(tag_values, list):
        return JsonResponse({'error': 'Field "tags" must be a list'}, status=400)

    try:
        slug_value = (payload.get('slug') or '').strip()
        if not slug_value:
            slug_value = slugify(title)
            if not slug_value:
                slug_value = uuid.uuid4().hex[:12]
        
        post = Post(
            title=title,
            slug=slug_value,
            description=(payload.get('description') or '').strip(),
            content=content,
            language=language,
            published_date=_parse_publish_datetime(payload.get('published_date')),
        )
        post.save()
        if tag_values:
            post.tags.set(_resolve_tags(tag_values))
    except ValidationError as exc:
        return JsonResponse({'error': exc.message_dict}, status=400)

    return JsonResponse(
        {
            'id': post.pk,
            'slug': post.slug,
            'language': post.language,
            'url': post.get_absolute_url(),
            'published_date': post.published_date.isoformat() if post.published_date else None,
        },
        status=201,
    )

def post_debug(request, slug):
    from django.http import JsonResponse
    post = Post.objects.filter(slug=slug).first()
    return JsonResponse({
        'exists': bool(post),
        'title': post.title if post else None,
        'published': post.published_date if post else None,
        'language': post.language if post else None
    })
    
class BaseBlogView:
    """Базовый класс для представлений блога"""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_lang'] = self.kwargs.get('lang', get_language())
        return context


class PostListView(BaseBlogView, ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 6
    
    def get_queryset(self):
        language = self.kwargs.get('lang', get_language())
        return Post.objects.filter(
            published_date__isnull=False,
            language=language
        ).select_related('translation_pair').prefetch_related('tags').order_by('-published_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.all()
        return context


class PostDetailView(BaseBlogView, DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        """Базовый queryset с фильтрацией опубликованных постов"""
        return Post.objects.filter(published_date__isnull=False)
    
    def get_object(self, queryset=None):
        """
        Улучшенная версия с:
        - Поддержкой всех языков из settings.LANGUAGES
        - Fallback на язык по умолчанию
        - Проверкой published_date
        """
        lang = self.kwargs.get('lang', get_language())
        slug = self.kwargs.get('slug')
        default_lang = settings.LANGUAGE_CODE[:2]
        
        # Пытаемся найти пост на запрошенном языке
        post = self.get_queryset().filter(
            slug=slug,
            language=lang
        ).first()
        
        if post:
            return post
            
        # Если не нашли, ищем оригинал на языке по умолчанию
        original_post = self.get_queryset().filter(
            slug=slug,
            language=default_lang
        ).first()
        
        if not original_post:
            raise Http404("Post not found")
            
        # Ищем перевод на запрошенный язык
        if original_post.translation_pair:
            translated_post = self.get_queryset().filter(
                translation_pair=original_post.translation_pair,
                language=lang
            ).first()
            if translated_post:
                return translated_post
        
        # Если перевода нет, возвращаем оригинал с предупреждением
        if lang != default_lang:
            self.extra_context = {'translation_warning': True}
        return original_post
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['post']
        
        # Добавляем текущий язык в контекст
        context['current_lang'] = self.kwargs.get('lang', get_language())
        
        # Собираем доступные переводы
        translations = {}
        if post.translation_pair:
            for lang_code, lang_name in settings.LANGUAGES:
                if lang_code != post.language:
                    trans_post = self.get_queryset().filter(
                        translation_pair=post.translation_pair,
                        language=lang_code
                    ).first()
                    if trans_post:
                        translations[lang_code] = {
                            'url': reverse('blog:post_detail', kwargs={
                                'lang': lang_code,
                                'slug': trans_post.slug
                            }),
                            'title': trans_post.title,
                            'language': lang_code
                        }
        
        context['available_translations'] = translations
        return context


class TagPostListView(BaseBlogView, ListView):
    model = Post
    template_name = 'blog/tag_posts.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # Получаем текущий язык из параметров URL
        current_lang = self.kwargs.get('lang', get_language())
        
        # Получаем посты, связанные с тегом и текущим языком
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return Post.objects.filter(
            tags=self.tag,
            language=current_lang,  # Фильтрация по языку
            published_date__isnull=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag  # Передаем текущий тег
        context['tags'] = Tag.objects.all()  # Все теги для отображения
        context['current_lang'] = self.kwargs.get('lang', get_language())  # Передаем текущий язык
        return context


@csrf_protect
def custom_image_upload(request):
    """Загрузка изображений с сохранением оригинальных имен"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    try:
        image_file = request.FILES['image']
        today = timezone.now().strftime('%Y/%m/%d')
        upload_path = os.path.join('uploads', today)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_path), exist_ok=True)
        
        # Генерация уникального имени файла
        filename = f"{uuid.uuid4().hex[:8]}_{image_file.name}"
        image_path = os.path.join(settings.MEDIA_ROOT, upload_path, filename)
        
        # Сохранение файла
        with open(image_path, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)
        
        # Оптимизация изображения
        try:
            with Image.open(image_path) as img:
                if max(img.width, img.height) > 1200:
                    img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                    img.save(image_path, optimize=True, quality=85)
        except Exception as img_error:
            print(f"Image optimization failed: {img_error}")
        
        file_url = f"{settings.MEDIA_URL.rstrip('/')}/{upload_path}/{filename}"
        return JsonResponse({'image_path': file_url, 'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
def check_image_exists(request):
    """Проверка существования изображений"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        
        if not filename:
            return JsonResponse({'error': 'Filename not provided'}, status=400)
        
        uploads_path = os.path.join(settings.MEDIA_ROOT, 'uploads')
        search_pattern = os.path.join(uploads_path, '**', f'*_{filename}')
        found_files = glob.glob(search_pattern, recursive=True)
        
        if found_files:
            relative_path = found_files[0].replace(settings.MEDIA_ROOT, '').replace('\\', '/')
            return JsonResponse({
                'success': True,
                'found_path': f"{settings.MEDIA_URL.rstrip('/')}{relative_path}"
            })
            
        return JsonResponse({'success': False, 'message': 'Image not found'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from django.utils import translation
from django.shortcuts import redirect
from django.conf import settings

def switch_language(request, lang_code):
    # Активируем язык
    translation.activate(lang_code)
    request.session[translation.LANGUAGE_SESSION_KEY] = lang_code
    
    # Получаем URL для возврата
    redirect_url = request.META.get('HTTP_REFERER')
    
    # Если нет реферера, перенаправляем на главную
    if not redirect_url:
        return redirect(f'/{lang_code}/')
    
    # Если URL содержит языковой код, заменяем его
    for code, _ in settings.LANGUAGES:
        if f'/{code}/' in redirect_url:
            return redirect(redirect_url.replace(f'/{code}/', f'/{lang_code}/'))
    
    # Если URL не содержит языкового кода, добавляем его
    return redirect(f'/{lang_code}/')