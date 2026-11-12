from django.shortcuts import render
from django.urls import path


def home(request):
    return render(request, "sales/index.html")


urlpatterns = [path("", home, name="home")]
