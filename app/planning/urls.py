from django.urls import path
from . import views

urlpatterns = [
    path("search/", views.search_results_view, name="search_results"),
    path("<uuid:project_id>/", views.project_page_view, name="project_page"),
]