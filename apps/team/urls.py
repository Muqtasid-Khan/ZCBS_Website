from django.urls import path
from . import views

app_name = "team"
urlpatterns = [path("", views.index, name="index"), path("archive/", views.archive, name="archive")]
