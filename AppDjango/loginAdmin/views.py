from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test

def es_admin(user):
    return user.is_authenticated and user.is_staff


def admin_login(request):
    return render(request, 'admin_login.html')

def index(request):
    return render(request, 'index.html')


# loginAdmin/views.py
def admin_menu(request):
    return render(request, 'admin_menu.html')

@user_passes_test(es_admin)
def admin_carga_jugador(request):
    return render(request, "admin_carga_jugador.html")

@user_passes_test(es_admin)
def menu(request):
    return render(request, "menu.html")

