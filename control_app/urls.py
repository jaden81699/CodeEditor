from django.urls import path
from control_app import views
from control_app.views import run_code, submit_all

app_name = "control_app"

urlpatterns = [
    path('run-code/', run_code, name='run-code'),
    path('editor/', views.editor, name='editor'),
    path('submit-all/', submit_all, name='submit-all'),

]
