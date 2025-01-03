from django.contrib import admin
from .models import Torneo,Equipo,TorneoJugador

# Register your models here.
admin.site.register(Torneo)
admin.site.register(Equipo)
admin.site.register(TorneoJugador)