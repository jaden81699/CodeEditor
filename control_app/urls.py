from django.urls import path
from control_app import views
from control_app.views import ControlLoginView

app_name = "control_app"

urlpatterns = [
    path("login/", ControlLoginView.as_view(), name="login"),
    path('register/', views.register_control, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path("thank-you/", views.thank_you, name="thank_you"),
]
