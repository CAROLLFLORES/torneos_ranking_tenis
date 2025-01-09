from django.contrib import admin
from .models import Torneo,Equipo,TorneoJugador,Cancha,Partido,ResultadoPartido

# Register your models here.
admin.site.register(Torneo)
admin.site.register(Equipo)
admin.site.register(TorneoJugador)
admin.site.register(Cancha)
admin.site.register(Partido)
admin.site.register(ResultadoPartido)