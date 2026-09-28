from django.urls import path

from support import views

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/<int:stage>/", views.chat, name="chat"),
    path("evaluation/", views.evaluate, name="evaluate"),
    path("state/correct/", views.correct, name="correct"),
    path("state/retention/", views.retention, name="retention"),
    path("state/delete/", views.delete_state, name="delete_state"),
    path("reset/<int:stage>/", views.reset, name="reset"),
]
