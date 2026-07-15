import json, re
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login as auth_login
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.conf import settings
from .models import AnkiNote, CardProgress

ANKI_MEDIA_URL = settings.STATIC_URL + 'anki/media/'

def fix_media_refs(text):
    """Заменяет ссылки на медиа в тексте на правильные URL"""
    if not text:
        return ''
    text = re.sub(
        r'\[sound:([^\]]+)\]',
        lambda m: f'<audio controls preload="none" style="height:32px;vertical-align:middle"><source src="{ANKI_MEDIA_URL}{m.group(1)}"></audio>',
        text
    )
    text = re.sub(
        r'<img([^>]*)src="([^"]+)"',
        lambda m: f'<img{m.group(1)}src="{ANKI_MEDIA_URL}{m.group(2)}"',
        text
    )
    return text


def study_view(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User
        user = User.objects.first()
        if user:
            auth_login(request, user)
    return render(request, 'anki/study.html')


@require_http_methods(['GET'])
def get_due_cards(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        total = AnkiNote.objects.count()
    except Exception as e:
        return JsonResponse({'error': f'БД anki недоступна: {str(e)}'}, status=500)

    now = timezone.now()
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User
        request.user = User.objects.first()

    studied_ids = list(CardProgress.objects.filter(
        user=request.user
    ).values_list('note_id', flat=True))

    due_progress = list(CardProgress.objects.filter(
        user=request.user, next_review__lte=now
    ).order_by('next_review')[:50])

    due_ids = [p.note_id for p in due_progress]
    due_notes = {n.note_id: n for n in AnkiNote.objects.filter(note_id__in=due_ids)}

    new_count = max(0, 20 - len(due_progress))
    if new_count > 0 and studied_ids:
        new_sample = list(AnkiNote.objects.exclude(note_id__in=studied_ids).order_by('?')[:new_count])
    elif new_count > 0:
        new_sample = list(AnkiNote.objects.order_by('?')[:new_count])
    else:
        new_sample = []

    due_data = []
    for prog in due_progress:
        note = due_notes.get(prog.note_id)
        if note:
            due_data.append(serialize_card(note, prog))

    new_data = [serialize_card(note, None) for note in new_sample]

    return JsonResponse({
        'total': total,
        'due_cards': due_data,
        'new_cards': new_data,
        'due_count': len(due_progress),
        'new_count': len(new_sample),
        'studied_count': len(studied_ids),
    })


@require_http_methods(['GET'])
def get_stats(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    now = timezone.now()
    due_count = CardProgress.objects.filter(user=request.user, next_review__lte=now).count()
    total_studied = CardProgress.objects.filter(user=request.user).count()

    intervals = {
        'new': total_studied - CardProgress.objects.filter(user=request.user, reps__gt=0).count(),
        'learning': CardProgress.objects.filter(user=request.user, reps__gt=0, reps__lt=3).count(),
        'young': CardProgress.objects.filter(user=request.user, interval__gte=1, interval__lt=21).count(),
        'mature': CardProgress.objects.filter(user=request.user, interval__gte=21).count(),
    }
    return JsonResponse({
        'due_count': due_count, 'total_studied': total_studied, 'intervals': intervals,
    })


@csrf_exempt
@require_http_methods(['POST'])
def submit_review(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        data = json.loads(request.body)
        note_id = int(data.get('note_id'))
        quality = int(data.get('quality', 0))
        if quality < 0 or quality > 5:
            return JsonResponse({'error': 'Quality must be 0-5'}, status=400)
        try:
            AnkiNote.objects.get(note_id=note_id)
        except AnkiNote.DoesNotExist:
            return JsonResponse({'error': 'Card not found'}, status=404)
        progress, created = CardProgress.objects.get_or_create(user=request.user, note_id=note_id)
        progress.process_response(quality)
        return JsonResponse({
            'success': True, 'next_review': progress.next_review.isoformat(),
            'interval': progress.interval, 'ease_factor': round(progress.ease_factor, 2),
            'reps': progress.reps,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def add_to_queue(request):
    """POST /anki/api/add-to-queue/ — добавить карточку в очередь изучения"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        data = json.loads(request.body)
        note_id = int(data.get('note_id'))
        try:
            note = AnkiNote.objects.get(note_id=note_id)
        except AnkiNote.DoesNotExist:
            return JsonResponse({'error': 'Card not found'}, status=404)
        progress, created = CardProgress.objects.get_or_create(
            user=request.user,
            note_id=note_id,
            defaults={
                'ease_factor': 2.5,
                'interval': 0,
                'reps': 0,
                'lapses': 0,
                'next_review': timezone.now(),
            }
        )
        if not created:
            # Reset progress if already exists
            progress.ease_factor = 2.5
            progress.interval = 0
            progress.reps = 0
            progress.lapses = 0
            progress.next_review = timezone.now()
            progress.save()
        return JsonResponse({'success': True, 'note_id': note_id})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(['GET'])
def search_cards(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'error': 'Query must be at least 2 characters'}, status=400)
    results = AnkiNote.objects.filter(
        Q(english__icontains=q) | Q(russian__icontains=q)
    )[:20]
    note_ids = [n.note_id for n in results]
    user_progress = {p.note_id: p for p in CardProgress.objects.filter(user=request.user, note_id__in=note_ids)}
    data = []
    for note in results:
        prog = user_progress.get(note.note_id)
        data.append(serialize_card(note, prog))
    return JsonResponse({'results': data, 'total': len(data)})


def serialize_card(note, progress=None):
    """Сериализация карточки — все поля сразу, испанский исключён"""
    result = {
        'note_id': note.note_id,
        'order_num': note.order_num,
        'english': note.english,
        'russian': note.russian,
        'ipa': note.ipa or '',
        'oxford_example': fix_media_refs(note.oxford_example or ''),
        'example_en_ru': fix_media_refs(note.example_en_ru or ''),
        'collocations': fix_media_refs(note.collocations or ''),
        'synonyms': fix_media_refs(note.synonyms or ''),
        'word_family': fix_media_refs(note.word_family or ''),
        'oxford_definition': fix_media_refs(note.oxford_definition or ''),
        'full_definition': fix_media_refs(note.full_definition or ''),
        'common_error': fix_media_refs(note.common_error or ''),
        'irregular_verbs': fix_media_refs(note.irregular_verbs or ''),
        'idioms_list': fix_media_refs(note.idioms_list or ''),
        'proverb': fix_media_refs(note.proverb or ''),
        'idiom': fix_media_refs(note.idiom or ''),
        'idiom_meaning': fix_media_refs(note.idiom_meaning or ''),
        'idiom_example': fix_media_refs(note.idiom_example or ''),
        'homonyms': fix_media_refs(note.homonym or ''),
        'homophones': fix_media_refs(note.homophones or ''),
        'en_sound': fix_media_refs(note.en_sound or ''),
        'longman_sound': fix_media_refs(note.longman_sound or ''),
        'card_image': note.card_image or '',
        'spanish': note.spanish or '',
        'tags': note.tags or '',
    }
    if progress:
        result['progress'] = {
            'ease_factor': round(progress.ease_factor, 2),
            'interval': progress.interval,
            'reps': progress.reps,
            'lapses': progress.lapses,
            'next_review': progress.next_review.isoformat() if progress.next_review else None,
            'last_review': progress.last_review.isoformat() if progress.last_review else None,
        }
    else:
        result['progress'] = None
    return result
