from django.db import models

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    categoria = models.CharField(max_length=10)

    def __str__(self):
        return self.categoria

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
