from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone


class AnkiNote(models.Model):
    """Модель для существующей таблицы anki_notes в БД anki (unmanaged)"""
    note_id = models.BigIntegerField(unique=True, null=True, blank=True)
    guid = models.CharField(max_length=20, blank=True, null=True)
    order_num = models.IntegerField(null=True, blank=True, verbose_name='Порядок')
    spanish = models.TextField(blank=True, null=True, verbose_name='Испанский')
    russian = models.TextField(blank=True, null=True, verbose_name='Русский')
    english = models.TextField(blank=True, null=True, verbose_name='Английский')
    example_en_ru = models.TextField(blank=True, null=True, verbose_name='Пример EN-RU')
    longman_sound = models.TextField(blank=True, null=True, verbose_name='Аудио Longman')
    longman_example = models.TextField(blank=True, null=True, verbose_name='Пример Longman')
    oxford_example = models.TextField(blank=True, null=True, verbose_name='Пример Oxford')
    oxford_example_cloze = models.TextField(blank=True, null=True, verbose_name='Oxford cloze')
    collocations = models.TextField(blank=True, null=True, verbose_name='Коллокации')
    oxford_3000_cloze = models.TextField(blank=True, null=True, verbose_name='Oxford 3000 cloze')
    oxford_definition = models.TextField(blank=True, null=True, verbose_name='Определение Oxford')
    ipa = models.CharField(max_length=100, blank=True, null=True, verbose_name='Транскрипция')
    en_sound = models.TextField(blank=True, null=True, verbose_name='Аудио EN')
    full_definition = models.TextField(blank=True, null=True, verbose_name='Полное определение')
    homonym = models.TextField(blank=True, null=True, verbose_name='Омоним')
    homophones = models.TextField(blank=True, null=True, verbose_name='Омофоны')
    synonyms = models.TextField(blank=True, null=True, verbose_name='Синонимы')
    word_family = models.TextField(blank=True, null=True, verbose_name='Семья слов')
    common_error = models.TextField(blank=True, null=True, verbose_name='Ошибки')
    irregular_verbs = models.TextField(blank=True, null=True, verbose_name='Непр. глаголы')
    idioms_list = models.TextField(blank=True, null=True, verbose_name='Идиомы')
    proverb = models.TextField(blank=True, null=True, verbose_name='Пословица')
    portuguese = models.TextField(blank=True, null=True, verbose_name='Португальский')
    french = models.TextField(blank=True, null=True, verbose_name='Французский')
    german = models.TextField(blank=True, null=True, verbose_name='Немецкий')
    idiom = models.TextField(blank=True, null=True, verbose_name='Идиома')
    idiom_meaning = models.TextField(blank=True, null=True, verbose_name='Значение идиомы')
    idiom_example = models.TextField(blank=True, null=True, verbose_name='Пример идиомы')
    card_image = models.TextField(blank=True, null=True, verbose_name='Изображение')
    tags = models.TextField(blank=True, null=True, verbose_name='Теги')

    class Meta:
        managed = False
        db_table = 'anki_notes'
        verbose_name = 'Карточка Anki'
        verbose_name_plural = 'Карточки Anki'

    def __str__(self):
        return self.english or self.spanish or f'Note #{self.note_id}'


class CardProgress(models.Model):
    """Прогресс изучения карточки пользователем (SM-2 алгоритм)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='anki_progress',
        verbose_name='Пользователь'
    )
    # Храним note_id как IntegerField (FK невозможен между разными БД)
    note_id = models.BigIntegerField(verbose_name='ID карточки')

    # SM-2 параметры
    ease_factor = models.FloatField(default=2.5, verbose_name='Фактор лёгкости')
    interval = models.IntegerField(default=0, verbose_name='Интервал (дни)')
    reps = models.IntegerField(default=0, verbose_name='Повторения')
    lapses = models.IntegerField(default=0, verbose_name='Ошибки')

    # Даты
    next_review = models.DateTimeField(
        default=timezone.now, verbose_name='Следующее повторение'
    )
    last_review = models.DateTimeField(
        null=True, blank=True, verbose_name='Последнее повторение'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Прогресс карточки'
        verbose_name_plural = 'Прогресс карточек'
        unique_together = ['user', 'note_id']
        ordering = ['next_review']
        indexes = [
            models.Index(fields=['user', 'next_review']),
            models.Index(fields=['user', '-reps']),
        ]

    def __str__(self):
        return f'{self.user} - card #{self.note_id}'

    def process_response(self, quality):
        """
        SM-2 алгоритм: обработка ответа пользователя
        quality: 0-5 (0=полный провал, 5=идеально)
        """
        if quality < 3:
            self.lapses += 1
            self.interval = 1
            self.reps = 0
        else:
            if self.reps == 0:
                self.interval = 1
            elif self.reps == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease_factor)
            self.reps += 1

        new_ef = self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if new_ef < 1.3:
            new_ef = 1.3
        self.ease_factor = new_ef

        self.last_review = timezone.now()
        self.next_review = timezone.now() + timedelta(days=self.interval)
        self.save()
