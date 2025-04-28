"""
URL configuration for CodeEditor project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, include
from django.contrib.auth import views as auth_views

from control_app.views import run_code
from editor import views
from editor.views import create_or_edit_questions, delete_question

urlpatterns = [
    path('admin/', admin.site.urls),
    path('e/', include('editor.urls'), ),
    path('c/', include('control_app.urls'), ),
    path('questions/', create_or_edit_questions, name='create-or-edit-questions'),
    path('questions/<int:question_id>/', create_or_edit_questions, name='create-or-edit-questions'),
    path('questions/delete/<int:question_id>/', delete_question, name='delete-question'),
]
