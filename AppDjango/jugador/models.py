from django.db import models

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nivel = models.IntegerField(default=0)  # Nuevo campo para Nivel
    edad = models.IntegerField(default=0)              # Nuevo campo para Edad
    tipo_juego = models.CharField(max_length=20,default='Sin tipo')  # Nuevo campo para Tipo de Juego

    def __str__(self):
        return f"Categoria: {self.nivel}+{self.edad}+{self.tipo_juego}"

class Jugador(models.Model):
    dni = models.CharField(max_length=8, primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    sexo = models.CharField(max_length=1)
    categorias = models.ManyToManyField(Categoria, through='JugadorCategoria')

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class JugadorCategoria(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('jugador', 'categoria')
