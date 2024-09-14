from django.shortcuts import render
from django.http import HttpResponse

def admin_login(request):
    return render(request, 'admin_login.html')

def index(request):
    return HttpResponse("probando")

# loginAdmin/views.py
def admin_menu(request):
    return render(request, 'admin_menu.html')


def admin_carga_jugador(request):
    return render(request, "admin_carga_jugador.html")

def admin_datos_jugador(request):
    return render(request, "admin_datos_jugador.html")

def menu(request):
    return render(request, "menu.html")

