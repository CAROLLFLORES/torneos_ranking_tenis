from django.db import models
from jugador.models import Categoria, Jugador
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# Modelo Torneo
class Torneo(models.Model):
    nombre = models.CharField(max_length=150)
    anio = models.PositiveBigIntegerField(validators=[MinValueValidator(0000), MaxValueValidator(9999)])

    def __str__(self):
        return f'{self.nombre} ({self.anio})'


# Modelo Partido
class Partido(models.Model):  
    id_partido = models.AutoField(primary_key=True)  
    fecha = models.DateTimeField(default=timezone.now)  
    hora = models.DateTimeField(default=timezone.now)   
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    id_cancha = models.ManyToManyField('Cancha', through='PartidoCancha')  # Corregido el nombre del modelo intermedio
    id_torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='partidos')  # Relación con Torneo

    def __str__(self):
        return f'Partido {self.id_partido} - {self.fecha} {self.hora}'


# Modelo Enfrentamiento
class Enfrentamiento(models.Model):  
    id_enfrentamiento = models.AutoField(primary_key=True)  # Corregido el uso de primary_key
    id_jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='enfrentamientos_como_jugador1')
    id_jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='enfrentamientos_como_jugador2')
    id_partido = models.ForeignKey(Partido, on_delete=models.CASCADE)

    def __str__(self):
        return f'Enfrentamiento {self.id_enfrentamiento} - {self.id_jugador1} vs {self.id_jugador2}'


# Modelo ResultadoPartido
class ResultadoPartido(models.Model):  
    id_resultado = models.AutoField(primary_key=True)
    id_partido = models.ForeignKey(Enfrentamiento, on_delete=models.CASCADE)
    id_jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='resultados_como_jugador1')
    id_jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='resultados_como_jugador2')
    resultado1 = models.IntegerField()
    resultado2 = models.IntegerField()

    def __str__(self):
        return f'Resultado {self.id_resultado}: {self.resultado1} - {self.resultado2}'


# Modelo PartidoCancha
class PartidoCancha(models.Model): 
    id_partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    id_cancha = models.ForeignKey('Cancha', on_delete=models.CASCADE)

    def __str__(self):
        return f'Partido {self.id_partido} - Cancha {self.id_cancha}'


# Modelo Cancha
class Cancha(models.Model):
    cancha = models.IntegerField()

    def __str__(self):
        return f'Cancha {self.cancha}'

        