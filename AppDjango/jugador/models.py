from django.db import models


class EstadoJugador(models.TextChoices):  # 👈 NO es tabla, es un enum
    ACTIVO   = 'ACT', 'Activo'
    INACTIVO = 'INA', 'Inactivo'
    BORRADO  = 'DEL', 'Borrado'

class JugadorQuerySet(models.QuerySet):
    def visibles(self):
        return self.exclude(estado=EstadoJugador.BORRADO)
    def activos(self):
        return self.filter(estado=EstadoJugador.ACTIVO)
    def inactivos(self):
        return self.filter(estado=EstadoJugador.INACTIVO)

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nivel = models.CharField(max_length=20, default='Sin nivel')  # Cambiado a CharField
    edad = models.CharField(max_length=20, default=0)                        # Nuevo campo para Edad
    tipo_juego = models.CharField(max_length=20, default='Sin tipo')  # Nuevo campo para Tipo de Juego
    genero = models.CharField(max_length=10, default='Sin tipo')  # Nuevo campo para Género

    def __str__(self):
        return f"{self.tipo_juego or 'N/A'}+{self.genero or 'N/A'}+{self.nivel or 'N/A'}+{self.edad or 'N/A'}"

class Jugador(models.Model):
    dni = models.AutoField(primary_key=True)  # Cambiado a AutoField
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    sexo = models.CharField(max_length=1, choices=[('F', 'Femenino'), ('M', 'Masculino')])  # Actualizado en el siguiente paso
    categorias = models.ManyToManyField(Categoria, through='JugadorCategoria')
    estado = models.CharField(
            max_length=3,
            choices=EstadoJugador.choices,
            default=EstadoJugador.ACTIVO,
            db_index=True
        )
    fecha_baja = models.DateField(null=True, blank=True)  # opcional, para auditar bajas
    observaciones = models.CharField(  max_length=200, default="Sin observaciones", blank=True )

    # 👈 enganchar el manager
    objects = JugadorQuerySet.as_manager()
    
    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class JugadorCategoria(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('jugador', 'categoria')


