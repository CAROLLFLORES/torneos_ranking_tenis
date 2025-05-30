from django.db import models
from jugador.models import Categoria, Jugador,JugadorCategoria
from django.utils import timezone
from datetime import date
from django.core.exceptions import ValidationError

class Torneo(models.Model):
    TIPO_CHOICES = [
        ('F', 'Femenino'),
        ('M', 'Masculino'),
        ('Mixto', 'Mixto'),
    ]

    TIPO_JUEGO_CHOICES = [
        ('Single', 'Single'),
        ('Doble', 'Doble'),
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
    tipo_juego = models.CharField(  # <- este es el campo nuevo
        max_length=10,
        choices=TIPO_JUEGO_CHOICES,
        default='Single'
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
    sede = models.ForeignKey('Sede', on_delete=models.CASCADE, related_name='canchas', null=True)

    def __str__(self):
        return f'Cancha {self.cancha} - {self.sede.nombre}'


    
    
class Sede(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


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

# Modelo Partido
class Partido(models.Model):
    torneo = models.ForeignKey('Torneo', on_delete=models.CASCADE)
    jugador1 = models.ForeignKey('jugador.Jugador', on_delete=models.CASCADE, related_name='partidos_jugador1', null=True, blank=True)
    jugador2 = models.ForeignKey('jugador.Jugador', on_delete=models.CASCADE, related_name='partidos_jugador2', null=True, blank=True)
    equipo1 = models.ForeignKey('Equipo', on_delete=models.CASCADE, related_name='partidos_equipo1', null=True, blank=True)
    equipo2 = models.ForeignKey('Equipo', on_delete=models.CASCADE, related_name='partidos_equipo2', null=True, blank=True)
    fecha = models.DateField()
    hora = models.TimeField()
    cancha = models.ForeignKey('Cancha', on_delete=models.CASCADE)
    jornada = models.IntegerField()

   
    
    
class ResultadoPartido(models.Model):
    partido = models.OneToOneField('Partido', on_delete=models.CASCADE, related_name='resultado')

    # Resultados para partidos individuales
    set1_jugador1 = models.IntegerField(null=True, blank=True)
    set1_jugador2 = models.IntegerField(null=True, blank=True)
    set2_jugador1 = models.IntegerField(null=True, blank=True)
    set2_jugador2 = models.IntegerField(null=True, blank=True)
    set3_jugador1 = models.IntegerField(null=True, blank=True)
    set3_jugador2 = models.IntegerField(null=True, blank=True)

    # Resultados para partidos dobles
    set1_equipo1 = models.IntegerField(null=True, blank=True)
    set1_equipo2 = models.IntegerField(null=True, blank=True)
    set2_equipo1 = models.IntegerField(null=True, blank=True)
    set2_equipo2 = models.IntegerField(null=True, blank=True)
    set3_equipo1 = models.IntegerField(null=True, blank=True)
    set3_equipo2 = models.IntegerField(null=True, blank=True)

    # Ganador puede ser un jugador o un equipo (solo se usará uno de los dos campos)
    ganador_jugador = models.ForeignKey(
        'jugador.Jugador', on_delete=models.SET_NULL, null=True, blank=True, related_name="partidos_ganados"
    )
    ganador_equipo = models.ForeignKey(
        'Equipo', on_delete=models.SET_NULL, null=True, blank=True, related_name="partidos_ganados"
    )


# Modelo intermedio PartidoCancha
class PartidoCancha(models.Model):
    id_partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    id_cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE)

    def __str__(self):
        return f'Partido {self.id_partido} - Cancha {self.id_cancha}'


from django.db import models
from torneo.models import Partido

class HistorialJornada(models.Model):
    torneo = models.ForeignKey("torneo.Torneo", on_delete=models.CASCADE)
    fecha = models.DateField()
    partidos = models.ManyToManyField(Partido)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Jornada {self.fecha} - {self.torneo.nombre}"



class MasterJugador(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    posicion = models.IntegerField()

    class Meta:
        unique_together = ('torneo', 'jugador', 'categoria')
        ordering = ['posicion']

    def __str__(self):
        return f"{self.posicion} - {self.jugador} ({self.torneo.nombre})"