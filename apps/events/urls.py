from django.urls import path
from . import views

app_name = "events"
urlpatterns = [
    path("", views.index, name="index"),
    path("archive/", views.archive, name="archive"),
    path("<slug:slug>/calendar.ics", views.ics, name="ics"),
    path("<slug:slug>/", views.detail, name="detail"),
]
