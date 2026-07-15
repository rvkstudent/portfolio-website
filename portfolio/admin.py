from django.contrib import admin
from .models import Portfolio, Project, WorkExperienceItem, EducationItem, CertificateItem, YearAchievements

# Удалим Project из встроенных моделей в Portfolio
class WorkExperienceInline(admin.TabularInline):
    model = WorkExperienceItem
    extra = 0

class EducationInline(admin.TabularInline):
    model = EducationItem
    extra = 0

class CertificateInline(admin.TabularInline):
    model = CertificateItem
    extra = 0

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Основная информация', {
            'fields': ('full_name', 'position', 'bio_title', 'bio_content', 'photo')
        }),
        ('Навыки', {
            'fields': ('skills',)
        }),
        ('Контактная информация', {
            'fields': ('email', 'github', 'linkedin', 'telegram', 'resume_pdf')
        }),
    )
    inlines = [WorkExperienceInline, EducationInline, CertificateInline]

# Отдельная регистрация Project
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title_ru', 'title_en', 'technology', 'is_active', 'order', 'created_date')
    list_filter = ('is_active', 'language', 'technology')
    search_fields = ('title_ru', 'title_en', 'description_ru', 'description_en', 'technology')
    list_editable = ('is_active', 'order')

@admin.register(YearAchievements)
class YearAchievementsAdmin(admin.ModelAdmin):
    list_display = ['year', 'summary_ru']
    list_filter = ['year']
    search_fields = ['year']