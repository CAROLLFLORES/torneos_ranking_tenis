from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

def es_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
def admin_login(request):
    return render(request, 'admin_login.html')

def index(request):
    return render(request, 'index.html')


@login_required
@user_passes_test(es_admin)
def admin_menu(request):
    return render(request, 'admin_menu.html')

@login_required
@user_passes_test(es_admin)
def admin_carga_jugador(request):
    return render(request, "admin_carga_jugador.html")

@login_required
@user_passes_test(es_admin)
def menu(request):
    return render(request, "menu.html")

