from django.urls import path

from . import views

urlpatterns = [
    path("tour/", views.tour, name="tour"),
]
