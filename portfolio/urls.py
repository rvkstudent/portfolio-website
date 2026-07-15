from django.urls import path
from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.projects_view, name='projects'),
    path('about/', views.about, name='about'),
    path('projects/<slug:slug>/', views.project_detail, name='project_detail'),  # Убрали параметр lang
]