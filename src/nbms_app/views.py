from django.shortcuts import render


def home(request):
    return render(request, "nbms_app/home.html")
