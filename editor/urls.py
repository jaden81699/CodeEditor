from django.contrib import admin
from django.urls import path
from . import views
from .views import run_code, submit_all, thank_you

app_name = "experimental_app"

urlpatterns = [
    path('run-code/', run_code, name='run-code'),
    path('editor/', views.editor, name='editor'),
    path('submit-all/', submit_all, name='submit-all'),
    path('thank-you/', thank_you, name='thank-you'),
]
