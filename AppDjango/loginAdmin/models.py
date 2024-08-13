from django.db import models

# Create your models here.

class usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    password = models.CharField(max_length=128)
    
class administrador(models.Model):
    id_administrador = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(usuario,on_delete=models.CASCADE)


    

