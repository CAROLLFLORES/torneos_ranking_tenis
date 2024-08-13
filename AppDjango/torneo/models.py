from django.db import models
from jugador.models import Categoria,Jugador

class partido(models.Model):
    id_partido = models.AutoField(primary_key=models.CASCADE)
    fecha = models.DateTimeField
    id_categoria = models.ForeignKey(Categoria,on_delete=models.CASCADE)
    
    
class enfrentamiento(models.Model):
    id_enfrentamiento = models.AutoField(primary_key=models.CASCADE)
    id_jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='enfrentamientos_como_jugador1')
    id_jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='enfrentamientos_como_jugador2')
    id_partido = models.ForeignKey(partido,on_delete=models.CASCADE)
    

class resultadoPartido (models.Model):
    id_resultado = models.AutoField(primary_key=models.CASCADE)
    id_partido = models.ForeignKey(enfrentamiento,on_delete=models.CASCADE)
    id_jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='resultados_como_jugador1')
    id_jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='resultados_como_jugador2')
    resultado1 = models.IntegerField()
    resultado2 = models.IntegerField()