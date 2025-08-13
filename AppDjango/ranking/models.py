from django.db import models
from jugador.models import Jugador, Categoria
from torneo.models import Torneo, Equipo



class Ranking(models.Model):
    id_ranking = models.AutoField(primary_key=True)
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="rankings")
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)
    posicion = models.IntegerField(default=0)
    pj = models.IntegerField(default=0)  # Partidos Jugados
    pg = models.IntegerField(default=0)  # Partidos Ganados
    pp = models.IntegerField(default=0)  # Partidos Perdidos
    sets = models.IntegerField(default=0)  # Sets ganados - perdidos
    games = models.IntegerField(default=0)  # Games Totales
    puntaje_total_categoria = models.IntegerField(default=0)
    puntaje_acumulador = models.IntegerField(default=0)
    bimestre = models.IntegerField(default=0)
    anio = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)  # 👈 Nuevo campo para visibilidad del jugador en ese torneo


    class Meta:
        unique_together = ('torneo', 'jugador', 'bimestre', 'anio', 'categoria')

    def __str__(self):
        return f'Ranking {self.torneo.nombre} - {self.jugador.nombre} ({self.categoria.nombre})'


class RankingEquipo(models.Model):
    id_ranking_equipo = models.AutoField(primary_key=True)
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="rankings_equipos")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)
    posicion = models.IntegerField(default=0)
    pj = models.IntegerField(default=0)
    pg = models.IntegerField(default=0)
    pp = models.IntegerField(default=0)
    sets = models.IntegerField(default=0)
    games = models.IntegerField(default=0)
    puntaje_total_categoria = models.IntegerField(default=0)
    puntaje_acumulador = models.IntegerField(default=0)
    bimestre = models.IntegerField(default=0)
    anio = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('torneo', 'equipo', 'bimestre', 'anio', 'categoria')

    def __str__(self):
        return f'Ranking {self.torneo.nombre} - {self.equipo}'