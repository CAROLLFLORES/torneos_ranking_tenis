from django.db import models

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nivel = models.CharField(max_length=20, default='Sin nivel')  # Cambiado a CharField
    edad = models.IntegerField(default=0)                        # Nuevo campo para Edad
    tipo_juego = models.CharField(max_length=20, default='Sin tipo')  # Nuevo campo para Tipo de Juego

    def __str__(self):
        return f"Categoria: {self.nivel}+{self.edad}+{self.tipo_juego}"

class Jugador(models.Model):
    dni = models.AutoField(primary_key=True)  # Cambiado a AutoField
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    sexo = models.CharField(max_length=1, choices=[('F', 'Femenino'), ('M', 'Masculino')])  # Actualizado en el siguiente paso
    categorias = models.ManyToManyField(Categoria, through='JugadorCategoria')

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class JugadorCategoria(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('jugador', 'categoria')
