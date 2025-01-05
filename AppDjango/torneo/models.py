from django.db import models
from jugador.models import Categoria, Jugador,JugadorCategoria
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
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)  # Relación con Torneo
    jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='partidos_jugador1')  # Jugador 1
    jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='partidos_jugador2')  # Jugador 2
    fecha = models.DateField()  # Fecha del partido
    hora = models.TimeField()  # Hora del partido
    cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE)  # Relación con Cancha
    jornada = models.IntegerField()  # Número de la jornada

    def __str__(self):
        return f"{self.torneo.nombre} - Jornada {self.jornada}: {self.jugador1} vs {self.jugador2}"




# Modelo intermedio PartidoCancha
class PartidoCancha(models.Model):
    id_partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    id_cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE)

    def __str__(self):
        return f'Partido {self.id_partido} - Cancha {self.id_cancha}'


#Modelo De crecion de equipos para torneo 
class Equipo(models.Model):
    # Nombre opcional del equipo (puede ser generado automáticamente)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    
    # Relaciones con los jugadores que forman el equipo
    jugador1 = models.ForeignKey(
        'jugador.Jugador',  # Referencia correcta a la app 'jugador' y el modelo 'Jugador'
        related_name='equipos_como_jugador1',
        on_delete=models.CASCADE
    )
    jugador2 = models.ForeignKey(
        'jugador.Jugador',  # Referencia correcta a la app 'jugador' y el modelo 'Jugador'
        related_name='equipos_como_jugador2',
        on_delete=models.CASCADE
    )
    
    # Relación con el torneo al que pertenece el equipo
    torneo = models.ForeignKey(
        'Torneo',  # Modelo Torneo está en la misma app
        related_name='equipos',
        on_delete=models.CASCADE
    )

    # Restricción para evitar duplicidad de equipos en el mismo torneo
    class Meta:
        unique_together = ('jugador1', 'jugador2', 'torneo')

    def __str__(self):
        return f"Equipo: {self.jugador1} y {self.jugador2} en Torneo {self.torneo.nombre}"
