from django.contrib import admin
from django.urls import path
from . import views
from .views import ExperimentalLoginView, run_code, submit_all, thank_you

app_name = "experimental_app"

urlpatterns = [
    path("login/", ExperimentalLoginView.as_view(), name="login"),
    path('logout/', views.experimental_logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('run-code/', run_code, name='run-code'),
    path('editor/', views.editor, name='editor'),
    path('submit-all/', submit_all, name='submit-all'),
    path('thank-you/', thank_you, name='thank-you'),


]
