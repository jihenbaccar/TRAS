"""
URL configuration for tras project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from trasapp.views import facial_expression_view
from trasapp import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
   path('detect-expression/', facial_expression_view, name='facial_expression'),
    path('check_expression/', views.check_expression, name='check_expression'),

    path('get-word/', views.get_word, name='get_word'),
    path('speak-word/', views.speak_word, name='speak_word'),
    path('assess-pronunciation/', views.assess_pronunciation, name='assess_pronunciation'),
    path('pronunciation/', views.pronunciation_view, name='pronunciation'),

    path('story/<int:story_id>/', views.story_detail, name='story_detail'),
    path('story/<int:story_id>/check_answer/', views.check_answer, name='check_answer'),
    path('audio/<str:filename>/', views.serve_audio, name='serve_audio'),  # Servir les fichiers audio

    #Stories management
    path('manage_stories/', views.manage_stories, name='manage_stories'),
    path('add-story/', views.add_story, name='add_story'),
    path('update-story/<int:story_id>/', views.update_story, name='update_story'),
    path('delete-story/<int:story_id>/', views.delete_story, name='delete_story'),

    # PRONUNCIATION MANAGEMENT

    path('manage_words/', views.manage_words, name='manage_words'),
    path('words/', views.get_words, name='get_words'),
    path('words/add/', views.add_word, name='add_word'),
    path('words/edit/<int:word_id>/', views.edit_word, name='edit_word'),
    path('words/delete/<int:word_id>/', views.delete_word, name='delete_word'),

   # path('edit/<int:word_id>/', views.edit_word, name='edit_word'),  # Correct path for edit_word view


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 


