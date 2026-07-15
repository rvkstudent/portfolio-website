from django.contrib import admin
from .models import CardProgress


@admin.register(CardProgress)
class CardProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'note_id', 'interval', 'ease_factor', 'next_review', 'reps', 'lapses']
    list_filter = ['next_review', 'user']
    search_fields = ['note_id', 'user__username']
    date_hierarchy = 'next_review'
    ordering = ['next_review']
