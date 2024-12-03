from django.db import models
from jugador.models import Categoria, Jugador
from django.utils import timezone
from datetime import date

class Torneo(models.Model):
    TIPO_CHOICES = [
        ('F', 'Femenino'),
        ('M', 'Masculino'),
        ('Mixto', 'Mixto'),
    ]
    
    nombre = models.CharField(max_length=150)
    fecha_inicio = models.DateField(default=date(2024, 1, 1))
    fecha_fin = models.DateField(null=True, blank=True)
    categorias = models.ManyToManyField(
        'jugador.Categoria',
        through='TorneoCategoria',
        related_name='torneos'
    )
    
    tipo = models.CharField(
        max_length=6,
        choices=TIPO_CHOICES,
        default='Mixto',
        editable=True
    )
    
    anio = models.PositiveIntegerField(default=date.today().year, editable=False)
    
    def save(self, *args, **kwargs):
        self.anio = self.fecha_inicio.year
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.nombre} ({self.anio})'

class TorneoCategoria(models.Model):
    torneo = models.ForeignKey(
        Torneo,
        on_delete=models.CASCADE,
        related_name='torneo_categorias'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='categoria_torneos'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['torneo', 'categoria'], name='unique_torneo_categoria')
        ]

    def __str__(self):
        return f'{self.torneo.nombre} - {self.categoria.nombre}'

# Modelo intermedio para Torneo y Jugador
class TorneoJugador(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='torneo_jugadores')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='jugador_torneos')

    class Meta:
        unique_together = ('torneo', 'jugador')

    def __str__(self):
        return f'{self.torneo.nombre} - {self.jugador.nombre} {self.jugador.apellido}'

# Modelo Cancha
class Cancha(models.Model):
    cancha = models.IntegerField()

    def __str__(self):
        return f'Cancha {self.cancha}'

# Modelo Partido
class Partido(models.Model):
    id_partido = models.AutoField(primary_key=True)
    fecha = models.DateTimeField(default=timezone.now)
    hora = models.DateTimeField(default=timezone.now)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    id_cancha = models.ManyToManyField('Cancha', through='PartidoCancha')
    id_torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='partidos')

    def __str__(self):
        return f'Partido {self.id_partido} - {self.fecha} {self.hora}'

# Modelo intermedio PartidoCancha
class PartidoCancha(models.Model):
    id_partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    id_cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE)

    def __str__(self):
        return f'Partido {self.id_partido} - Cancha {self.id_cancha}'
