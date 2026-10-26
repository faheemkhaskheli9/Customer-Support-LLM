from django.urls import path

from support import views

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/<int:stage>/", views.chat, name="chat"),
    path("evaluation/", views.evaluate, name="evaluate"),
    path("evaluation/rag/", views.rag_evaluate, name="rag_evaluate"),
    path("evaluation/tools/", views.tool_evaluate, name="tool_evaluate"),
    path("evaluation/health/", views.health_evaluate, name="health_evaluate"),
    path("report/", views.report, name="report"),
    path("report.md", views.report_markdown, name="report_markdown"),
    path("state/correct/", views.correct, name="correct"),
    path("state/retention/", views.retention, name="retention"),
    path("state/delete/", views.delete_state, name="delete_state"),
    path("reset/<int:stage>/", views.reset, name="reset"),
]
