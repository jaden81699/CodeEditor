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

import control_app
from control_app.views import ControlLoginView
from editor import views as experimental_views
from control_app import views as control_views
from editor.views import create_or_edit_questions, delete_question

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", ControlLoginView.as_view(), name="login"),
    path('register/', control_app.views.register_control, name='register'),
    path('logout/', control_app.views.logout_view, name='logout'),
    path("thank-you/", control_app.views.thank_you, name="thank-you"),
    path('e/', include('editor.urls'), ),
    path('c/', include('control_app.urls'), ),
    path('questions/', create_or_edit_questions, name='create-or-edit-questions'),
    path('questions/<int:question_id>/', create_or_edit_questions, name='create-or-edit-questions'),
    path('questions/delete/<int:question_id>/', delete_question, name='delete-question'),
    path("pre-assessment/", control_views.pre_assessment_questionnaire, name="pre-assessment"),
    path("pre-assessment-complete/", control_views.pre_assessment_complete, name="pre-survey-complete"),
    path("post-assessment/", control_app.views.post_assessment_questionnaire, name="post-assessment"),
    path("post-assessment-complete/", control_app.views.post_assessment_complete, name="post-assessment-complete"),
    path("ai/telemetry/", control_app.views.ai_telemetry, name="ai_telemetry"),
]
