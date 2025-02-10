from django.db import models
from jugador.models import Jugador, Categoria
from torneo.models import Torneo  # Importa Torneo correctamente

class Ranking(models.Model):
    id_ranking = models.AutoField(primary_key=True)
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="rankings")  # Relación correcta con Torneo
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    posicion = models.IntegerField()
    pj = models.IntegerField()
    pg = models.IntegerField()
    games = models.IntegerField()
    puntaje_total_categoria = models.IntegerField()
    puntaje_acumulador = models.IntegerField()
    bimestre = models.IntegerField()
    anio = models.IntegerField()

    class Meta:
        unique_together = ('torneo', 'jugador', 'bimestre', 'anio', 'categoria')  # Asegúrate de que 'torneo' está en el modelo

    def __str__(self):
        return f'Ranking {self.torneo.nombre} - {self.jugador.nombre} ({self.categoria.nombre})'
