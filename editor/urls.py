from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('editor/', views.editor, name='editor'),
    path('questions/', views.create_or_edit_questions, name='create-or-edit-questions'),
    path('questions/<int:question_id>/', views.create_or_edit_questions, name='create-or-edit-questions'),
    path('questions/delete/<int:question_id>/', views.delete_question, name='delete-question'),
    path('submit-code/', views.submit_code, name='submit-code'),
    path('run-code/', views.run_code, name='run-code'),

]
