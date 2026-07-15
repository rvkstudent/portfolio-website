from django.shortcuts import render, get_object_or_404, redirect
from .models import Project, Portfolio, WorkExperienceItem, EducationItem, CertificateItem, YearAchievements
from django.db.models import Min, Max
from markdownx.utils import markdownify


def home(request):
    # Перенаправляем на страницу проектов (по годам)
    return redirect('portfolio:projects')

def about(request):
    portfolio = Portfolio.objects.first()
    certificates = CertificateItem.objects.filter(portfolio=portfolio) if portfolio else []
    education = EducationItem.objects.filter(portfolio=portfolio) if portfolio else []
    experience = WorkExperienceItem.objects.filter(portfolio=portfolio) if portfolio else []
    
    return render(request, 'portfolio/about.html', {
        'portfolio': portfolio,
        'certificates': certificates,
        'education': education,
        'experience': experience,
    })

def project_detail(request, slug):
    # Получаем текущий язык
    current_lang = request.LANGUAGE_CODE
    
    # Проверяем, есть ли проект на текущем языке
    if current_lang == 'ru':
        # Проверка наличия русского контента
        project_exists = Project.objects.filter(
            slug=slug, 
            is_active=True,
            title_ru__isnull=False,
            description_ru__isnull=False
        ).exists()
    else:
        # Проверка наличия английского контента
        project_exists = Project.objects.filter(
            slug=slug, 
            is_active=True,
            title_en__isnull=False,
            description_en__isnull=False
        ).exists()
    
    # Если проект не существует на текущем языке
    if not project_exists:
        # Проверяем, есть ли проект на другом языке
        project_any_lang = Project.objects.filter(slug=slug, is_active=True).first()
        
        # Если проект существует на другом языке, перенаправляем
        if project_any_lang:
            # Определяем, на каком языке доступен проект
            if current_lang != 'ru' and project_any_lang.title_ru and project_any_lang.description_ru:
                # Перенаправляем на русскую версию
                return redirect(f'/ru/projects/{slug}/')
            elif current_lang != 'en' and project_any_lang.title_en and project_any_lang.description_en:
                # Перенаправляем на английскую версию
                return redirect(f'/en/projects/{slug}/')
    
    # Получаем проект для текущего языка
    project = get_object_or_404(Project, slug=slug, is_active=True)
    
    return render(request, 'portfolio/project_detail.html', {'project': project})

def projects_view(request):
    selected_year = request.GET.get('year')

    # Получаем доступные года из поля created_date
    years_qs = Project.objects.dates('created_date', 'year', order='DESC')
    year_list = [d.year for d in years_qs]

    # Если год не выбран, берем последний (самый свежий)
    if not selected_year and year_list:
        selected_year = year_list[0]
    else:
        try:
            selected_year = int(selected_year) if selected_year else None
        except (ValueError, TypeError):
            selected_year = year_list[0] if year_list else None

    # Получаем проекты за выбранный год (или пустой QuerySet)
    if selected_year:
        projects = Project.objects.filter(created_date__year=selected_year, is_active=True).order_by('-order', '-created_date')
        achievements = YearAchievements.objects.filter(year=selected_year).first()
    else:
        projects = Project.objects.filter(is_active=True).order_by('-order', '-created_date')
        achievements = None

    # Подготовка HTML из Markdown для полей YearAchievements (если есть)
    achievements_html = None
    page_title = None
    page_subtitle = None
    seo_data = {}
    
    if achievements:
        lang = getattr(request, 'LANGUAGE_CODE', 'ru')
        if lang == 'ru':
            tech = markdownify(achievements.tech_stack_ru or '')
            business = markdownify(achievements.business_results_ru or '')
            keys = markdownify(achievements.key_competencies_ru or '')
            summary = markdownify(achievements.summary_ru or '')
            projects_md = markdownify(achievements.projects_ru or '')
            learning = markdownify(achievements.learning_development_ru or '')
            page_title = achievements.page_title_ru or f"Профессиональные достижения {selected_year}"
            page_subtitle = achievements.page_subtitle_ru or ''
            
            # SEO данные
            seo_data = {
                'meta_title': achievements.meta_title_ru or page_title,
                'meta_description': achievements.meta_description_ru or '',
                'meta_keywords': achievements.meta_keywords_ru or '',
                'og_image': achievements.og_image.url if achievements.og_image else '',
            }
        else:
            tech = markdownify(achievements.tech_stack_en or '')
            business = markdownify(achievements.business_results_en or '')
            keys = markdownify(achievements.key_competencies_en or '')
            summary = markdownify(achievements.summary_en or '')
            projects_md = markdownify(achievements.projects_en or '')
            learning = markdownify(achievements.learning_development_en or '')
            page_title = achievements.page_title_en or f"Professional Achievements {selected_year}"
            page_subtitle = achievements.page_subtitle_en or ''
            
            # SEO данные
            seo_data = {
                'meta_title': achievements.meta_title_en or page_title,
                'meta_description': achievements.meta_description_en or '',
                'meta_keywords': achievements.meta_keywords_en or '',
                'og_image': achievements.og_image.url if achievements.og_image else '',
            }

        achievements_html = {
            'tech_stack': tech,
            'business_results': business,
            'key_competencies': keys,
            'summary': summary,
            'projects': projects_md,
            'learning_development': learning,
        }

    context = {
        'projects': projects,
        'achievements': achievements,
        'achievements_html': achievements_html,
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'seo_data': seo_data,
        'years': year_list,
        'selected_year': selected_year,
    }
    return render(request, 'portfolio/projects.html', context)