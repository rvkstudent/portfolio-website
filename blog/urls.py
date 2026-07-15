from django.urls import path
from . import views
from .views import TagPostListView, PostDetailView

app_name = 'blog'

urlpatterns = [
    # Явное указание языка в URL
    path('post-debug/<slug:slug>/', views.post_debug, name='post_debug'),
    path('<str:lang>/', views.PostListView.as_view(), name='post_list'),
    
    # Fallback URL (использует язык из настроек)
    path('', views.PostListView.as_view(), name='post_list_fallback'),
    
    # Остальные URL остаются без изменений
    path('<str:lang>/post/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail_fallback'),
    path('tag/<slug:slug>/', views.TagPostListView.as_view(), name='tag_posts_fallback'),

    path('<str:lang>/tag/<slug:slug>/', TagPostListView.as_view(), name='tag_posts'),

    
]