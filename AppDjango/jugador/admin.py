from django.contrib import admin
from .models import Categoria,Jugador,JugadorCategoria

# Register your models here
admin.site.register(Categoria)
admin.site.register(Jugador)
admin.site.register(JugadorCategoria)