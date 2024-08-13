from django.db import models
from jugador.models import Jugador,Categoria

class Ranking(models.Model):
    id_ranking = models.AutoField(primary_key=True)
    jugador= models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria,on_delete=models.CASCADE)
    posicion = models.IntegerField()
    pj = models.IntegerField()
    pg = models.IntegerField()
    puntaje_total_categoria = models.IntegerField()
    puntaje_acumulador = models.IntegerField()
    bimestre = models.IntegerField()
    anio = models.IntegerField()

    class Meta:
        unique_together = ('jugador', 'bimestre', 'anio','categoria')
