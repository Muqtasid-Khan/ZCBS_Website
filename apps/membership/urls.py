from django.urls import path
from . import views

app_name = "membership"
urlpatterns = [path("", views.join, name="join"), path("thank-you/", views.thanks, name="thanks")]
