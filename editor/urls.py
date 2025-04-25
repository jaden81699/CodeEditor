from django.contrib import admin
from django.urls import path
from . import views
from .views import ExperimentalLoginView

app_name = "experimental_app"

urlpatterns = [
    path("login/", ExperimentalLoginView.as_view(), name="login"),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),

]
