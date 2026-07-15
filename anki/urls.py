from django.urls import path
from . import views

app_name = 'anki'

urlpatterns = [
    # Основная страница
    path('', views.study_view, name='study'),
    
    # API для карточек
    path('api/due/', views.get_due_cards, name='api_due'),
    path('api/stats/', views.get_stats, name='api_stats'),
    path('api/submit/', views.submit_review, name='api_submit'),
    path('api/search/', views.search_cards, name='api_search'),
    path('api/add-to-queue/', views.add_to_queue, name='api_add_to_queue'),
]
