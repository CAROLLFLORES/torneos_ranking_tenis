from django.shortcuts import render

# Create your views here.
# MVC = modelo vista controlador  -> hay acciones (metodos)
# MVT = modelo vista template -> hay acciones (metodos)

from django.http import HttpResponse

def admin_login(request):
    return render(request, 'admin_login.html')

def index(request):
    return HttpResponse("probando")

def admin_menu(request):
    return render(request, "admin_menu.html")

def admin_carga_jugador(request):
    return render(request, "admin_carga_jugador.html")