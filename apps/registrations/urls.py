from django.urls import path
from . import views

app_name = "registrations"
urlpatterns = [
    path("find/", views.lookup, name="lookup"),
    path("staff/checkin/", views.checkin, name="checkin"),
    path("staff/dashboard/", views.dashboard, name="dashboard"),
    path("staff/export/<int:event_id>/<slug:kind>.xlsx", views.export, name="export"),
    path("my/<str:token>/", views.mine, name="mine"),
    path("my/<str:token>/status.json", views.pass_status, name="pass_status"),
    path("<slug:slug>/", views.register, name="register"),
]
